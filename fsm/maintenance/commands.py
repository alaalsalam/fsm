from __future__ import annotations

import frappe
from frappe import _

from fsm.maintenance.access import require_occurrence_access, require_plan_access
from fsm.maintenance.engine import (
	generate_occurrences,
	release_occurrences,
	reschedule_occurrence,
	skip_occurrence,
)
from fsm.security.policy import require_manager_scope, validate_allowed_fields
from fsm.service_operations.events import append_event

PLAN_FIELDS = {
	"plan_title",
	"customer",
	"company",
	"customer_site",
	"service_contract",
	"start_date",
	"end_date",
	"timezone",
	"forecast_horizon_days",
	"due_window_days",
	"catch_up_policy",
	"dst_policy",
	"equipment",
	"lines",
	"notes",
}
PLAN_UPDATE_FIELDS = PLAN_FIELDS - {"customer", "company"}
TRANSITIONS = {
	"Draft": {"Active", "Cancelled"},
	"Active": {"Paused", "Completed", "Cancelled"},
	"Paused": {"Active", "Completed", "Cancelled"},
	"Completed": set(),
	"Cancelled": set(),
}


def _result(doc):
	return frappe.get_doc(doc.doctype, doc.name).as_dict()


@frappe.whitelist()
def create_plan(**values):
	validate_allowed_fields(values, PLAN_FIELDS)
	require_manager_scope(values.get("company"))
	doc = frappe.get_doc({"doctype": "Maintenance Plan", "status": "Draft", **values})
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	append_event("MaintenancePlanCreated", doc, to_status="Draft", source="Console")
	return _result(doc)


@frappe.whitelist()
def update_plan(maintenance_plan: str, **values):
	validate_allowed_fields(values, PLAN_UPDATE_FIELDS)
	doc = require_plan_access(maintenance_plan, "write", manager_only=True)
	if doc.status in {"Completed", "Cancelled"}:
		frappe.throw(_("A terminal Maintenance Plan cannot be edited."))
	before_revision = doc.revision
	doc.update(values)
	doc.flags.fsm_command = True
	doc.save()
	if doc.revision != before_revision and doc.status == "Active":
		generate_occurrences(doc.name)
	return _result(doc)


@frappe.whitelist()
def transition_plan(maintenance_plan: str, status: str, reason: str | None = None, source="API"):
	doc = require_plan_access(maintenance_plan, "write", manager_only=True)
	if status not in TRANSITIONS.get(doc.status, set()):
		frappe.throw(_("Illegal Maintenance Plan transition from {0} to {1}.").format(doc.status, status))
	previous = doc.status
	doc.flags.fsm_command = True
	doc.status = status
	doc.save()
	append_event(
		"MaintenancePlanStatusChanged",
		doc,
		from_status=previous,
		to_status=status,
		source=source,
		metadata={"reason": reason} if reason else None,
	)
	if status == "Active":
		generate_occurrences(doc.name)
	return _result(doc)


@frappe.whitelist()
def generate_plan_occurrences(maintenance_plan: str, horizon_date: str | None = None):
	doc = require_plan_access(maintenance_plan, "write", manager_only=True)
	return {"maintenance_plan": doc.name, "occurrences": generate_occurrences(doc.name, horizon_date)}


@frappe.whitelist()
def release_plan_occurrences(maintenance_plan: str | None = None, occurrence_names=None):
	if maintenance_plan:
		doc = require_plan_access(maintenance_plan, "write", manager_only=True)
		names = frappe.get_all(
			"Maintenance Occurrence", filters={"maintenance_plan": doc.name}, pluck="name", limit=10000
		)
	else:
		names = frappe.parse_json(occurrence_names) if isinstance(occurrence_names, str) else occurrence_names
		if not names:
			frappe.throw(_("Select a Maintenance Plan or occurrences."))
		for name in names:
			require_occurrence_access(name, "write", manager_only=True)
	return {"jobs": release_occurrences(names)}


@frappe.whitelist()
def skip_plan_occurrence(occurrence: str, reason: str):
	doc = require_occurrence_access(occurrence, "write", manager_only=True)
	if not (reason or "").strip():
		frappe.throw(_("Skip reason is required."), frappe.ValidationError)
	return _result(skip_occurrence(doc.name, reason.strip()))


@frappe.whitelist()
def reschedule_plan_occurrence(occurrence: str, due_date: str):
	doc = require_occurrence_access(occurrence, "write", manager_only=True)
	return _result(reschedule_occurrence(doc.name, due_date))
