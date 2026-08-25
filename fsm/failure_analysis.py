# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime, nowdate

from fsm.security.policy import require_job_access, validate_allowed_fields
from fsm.service_operations.events import append_event

TRANSITIONS = {
	"Draft": {"Inspection", "Cancelled"},
	"Inspection": {"Analysis", "Cancelled"},
	"Analysis": {"Root Cause Identified", "Cancelled"},
	"Root Cause Identified": {"Corrective Action", "Cancelled"},
	"Corrective Action": {"Verification", "Cancelled"},
	"Verification": {"Closed", "Corrective Action", "Cancelled"},
	"Closed": set(),
	"Cancelled": set(),
}
CREATE_FIELDS = {
	"service_visit",
	"inspection",
	"failure_code",
	"symptom",
	"severity",
	"safety_risk",
}
UPDATE_FIELDS = {"failure_code", "symptom", "severity", "safety_risk", "root_cause", "corrective_action", "verification"}
PRIORITIES = {"Observation": "Low", "Minor": "Medium", "Major": "High", "Critical": "Urgent"}
PRIORITY_ORDER = ["Low", "Medium", "High", "Urgent"]


def _analysis(name: str, permission_type: str = "read"):
	doc = frappe.get_doc("Failure Analysis", name)
	require_job_access(doc.service_job, permission_type)
	return doc


def _result(doc):
	return frappe.get_doc(doc.doctype, doc.name).as_dict()


@frappe.whitelist()
def create_failure_analysis(service_job: str, installed_equipment: str, **values):
	validate_allowed_fields(values, CREATE_FIELDS)
	job = require_job_access(service_job, "write")
	if not any(row.installed_equipment == installed_equipment for row in job.equipment):
		frappe.throw(_("Installed Equipment must be linked to the Service Job."))
	window = int(frappe.db.get_single_value("Service Settings", "repeat_failure_window_days") or 90)
	repeat_count = frappe.db.count(
		"Failure Analysis",
		{
			"installed_equipment": installed_equipment,
			"status": ["!=", "Cancelled"],
			"creation": [">=", add_days(nowdate(), -window)],
		},
	)
	severity = values.get("severity") or "Major"
	escalation_count = int(frappe.db.get_single_value("Service Settings", "repeat_failure_escalation_count") or 2)
	escalated = bool(values.get("safety_risk") or severity == "Critical" or repeat_count >= escalation_count)
	priority = _priority_suggestion(severity, repeat_count, escalated)
	doc = frappe.get_doc(
		{
			"doctype": "Failure Analysis",
			"service_job": job.name,
			"installed_equipment": installed_equipment,
			"status": "Draft",
			"repeat_count": repeat_count,
			"repeat_failure": int(repeat_count > 0),
			"escalated": int(escalated),
			"priority_suggestion": priority,
			**values,
		}
	)
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	append_event(
		"FailureAnalysisCreated",
		doc,
		to_status="Draft",
		source="Mobile",
		metadata={"repeat_count": repeat_count, "priority_suggestion": priority, "escalated": escalated},
	)
	return _result(doc)


@frappe.whitelist()
def update_failure_analysis(failure_analysis: str, **values):
	validate_allowed_fields(values, UPDATE_FIELDS)
	doc = _analysis(failure_analysis, "write")
	if doc.status in {"Closed", "Cancelled"}:
		frappe.throw(_("Terminal Failure Analysis records are immutable."))
	doc.update(values)
	doc.flags.fsm_command = True
	doc.save()
	append_event("FailureAnalysisUpdated", doc, source="Console", metadata={"fields": sorted(values)})
	return _result(doc)


@frappe.whitelist()
def transition_failure_analysis(failure_analysis: str, status: str, reason: str | None = None):
	doc = _analysis(failure_analysis, "write")
	if status not in TRANSITIONS.get(doc.status, set()):
		frappe.throw(_("Invalid Failure Analysis transition from {0} to {1}.").format(doc.status, status))
	_validate_transition_evidence(doc, status, reason)
	old = doc.status
	doc.status = status
	if status in {"Closed", "Cancelled"}:
		doc.closed_on = now_datetime()
	doc.flags.fsm_command = True
	doc.save()
	append_event(
		"FailureAnalysisStatusChanged",
		doc,
		from_status=old,
		to_status=status,
		source="Mobile",
		metadata={"reason": reason},
	)
	return _result(doc)


@frappe.whitelist()
def apply_priority_suggestion(failure_analysis: str):
	doc = _analysis(failure_analysis, "write")
	job = require_job_access(doc.service_job, "write", manager_only=True)
	if not doc.priority_suggestion:
		frappe.throw(_("No priority suggestion is available."))
	old = job.priority
	if old == doc.priority_suggestion:
		return {"job": job.name, "priority": old, "changed": False}
	job.priority = doc.priority_suggestion
	job.flags.fsm_command = True
	job.save()
	append_event(
		"JobPriorityChangedFromFailureAnalysis",
		job,
		source="Console",
		metadata={"failure_analysis": doc.name, "from_priority": old, "to_priority": job.priority},
	)
	return {"job": job.name, "priority": job.priority, "changed": True}


@frappe.whitelist()
def list_failure_analyses(
	service_job: str | None = None,
	installed_equipment: str | None = None,
	status: str | None = None,
	limit: int = 100,
):
	filters = {}
	if service_job:
		require_job_access(service_job, "read")
		filters["service_job"] = service_job
	if installed_equipment:
		filters["installed_equipment"] = installed_equipment
	if status:
		filters["status"] = status
	return frappe.get_list(
		"Failure Analysis",
		filters=filters,
		fields=[
			"name", "status", "service_job", "service_visit", "installed_equipment", "inspection",
			"failure_code", "symptom", "severity", "safety_risk", "repeat_failure", "repeat_count",
			"escalated", "priority_suggestion", "modified",
		],
		order_by="modified desc",
		limit=max(1, min(int(limit), 200)),
	)


@frappe.whitelist()
def get_failure_analysis(failure_analysis: str):
	return _result(_analysis(failure_analysis, "read"))


def _priority_suggestion(severity: str, repeat_count: int, escalated: bool) -> str:
	priority = PRIORITIES.get(severity, "Medium")
	if repeat_count > 0:
		priority = PRIORITY_ORDER[min(PRIORITY_ORDER.index(priority) + 1, len(PRIORITY_ORDER) - 1)]
	if escalated:
		priority = "Urgent"
	return priority


def _validate_transition_evidence(doc, status: str, reason: str | None):
	if status == "Root Cause Identified" and not doc.root_cause:
		frappe.throw(_("Record the root cause before identifying it."))
	if status == "Corrective Action" and not doc.corrective_action:
		frappe.throw(_("Record the corrective action before starting it."))
	if status == "Closed" and not doc.verification:
		frappe.throw(_("Record verification before closing the analysis."))
	if status == "Cancelled" and not reason:
		frappe.throw(_("A cancellation reason is required."))
