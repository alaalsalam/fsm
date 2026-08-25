from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from fsm.security.policy import require_job_access, validate_allowed_fields
from fsm.service_operations.events import append_event

REPORT_TYPES = {"Service Report", "Inspection Report", "Preventive Maintenance Report"}
CERTIFICATE_TYPES = {"Refill Certificate", "Hydro Test Certificate"}
TRANSITIONS = {"Draft": {"Generated"}, "Generated": {"Customer Review"}, "Customer Review": {"Customer Signed"}, "Customer Signed": {"Verified"}, "Verified": {"Submitted"}, "Submitted": set()}
UPDATE_FIELDS = {"work_performed", "recommendations", "customer_name", "customer_signature", "signature_refused", "refusal_reason"}


def _report(name: str, permission_type: str = "read"):
	doc = frappe.get_doc("Service Report", name)
	require_job_access(doc.service_job, permission_type)
	return doc


def _certificate(name: str, permission_type: str = "read"):
	doc = frappe.get_doc("Service Certificate", name)
	require_job_access(doc.service_job, permission_type)
	return doc


def _rows(doctype: str, job: str, fields: list[str], job_field: str = "service_job"):
	return frappe.get_all(doctype, filters={job_field: job}, fields=fields, order_by="creation asc")


def _snapshot(job):
	return {
		"schema_version": 1,
		"captured_on": str(now_datetime()),
		"job": {key: job.get(key) for key in ("name", "customer", "customer_name", "company", "service_address", "service_type", "status", "phase", "priority", "assigned_service_team", "team_leader", "primary_technician", "completed_on", "service_contract", "coverage_status", "quotation", "sales_invoice", "actual_hours", "labor_cost", "materials_cost", "total_cost", "notes")},
		"equipment": [row.as_dict() for row in job.equipment],
		"visits": _rows("Service Visit", job.name, ["name", "status", "service_team", "primary_technician", "actual_check_in", "actual_completion", "visit_notes"]),
		"inspections": _rows("Equipment Inspection", job.name, ["name", "installed_equipment", "inspection_template", "technician", "overall_result", "completed_on", "notes"]),
		"failures": _rows("Failure Analysis", job.name, ["name", "installed_equipment", "failure_code", "symptom", "root_cause", "severity", "corrective_action", "verification", "status"]),
		"materials": _rows("Stock Entry", job.name, ["name", "stock_entry_type", "docstatus", "posting_date", "fsm_material_action", "total_outgoing_value", "total_incoming_value"], "fsm_service_job"),
		"workshop": _rows("Service Return", job.name, ["name", "status", "installed_equipment", "quotation", "sales_invoice", "repair_notes", "testing_result", "quality_result", "final_outcome"]),
	}


@frappe.whitelist()
def generate_service_report(service_job: str, report_type: str = "Service Report", generation_key: str | None = None):
	job = require_job_access(service_job, "write")
	if report_type not in REPORT_TYPES:
		frappe.throw(_("Unsupported report type."))
	key = generation_key or f"{job.name}:{report_type}:1"
	if existing := frappe.db.get_value("Service Report", {"generation_key": key}, "name"):
		return frappe.get_doc("Service Report", existing).as_dict()
	revision = cint(
		frappe.db.get_value(
			"Service Report",
			{"service_job": job.name, "report_type": report_type},
			"revision",
			order_by="revision desc",
		)
	) + 1
	doc = frappe.get_doc({"doctype": "Service Report", "service_job": job.name, "report_type": report_type, "revision": revision, "generation_key": key, "status": "Draft", "customer": job.customer, "company": job.company, "customer_site": job.equipment[0].customer_site if job.equipment else None, "snapshot": json.dumps(_snapshot(job), default=str, ensure_ascii=False, sort_keys=True)})
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	append_event("ServiceReportCreated", doc, to_status="Draft", source="Console", metadata={"type": report_type, "revision": revision})
	return doc.as_dict()


@frappe.whitelist()
def update_service_report(service_report: str, **values):
	validate_allowed_fields(values, UPDATE_FIELDS)
	doc = _report(service_report, "write")
	if doc.status in {"Verified", "Submitted"}:
		frappe.throw(_("Verified and Submitted reports cannot be edited."))
	values["signature_refused"] = cint(values.get("signature_refused", doc.signature_refused))
	doc.update(values)
	if values.get("customer_signature") or values.get("signature_refused"):
		doc.signature_timestamp = now_datetime()
	doc.flags.fsm_command = True
	doc.flags.ignore_permissions = True
	doc.save()
	append_event("ServiceReportUpdated", doc, source="Mobile", metadata={"fields": sorted(values)})
	return doc.as_dict()


@frappe.whitelist()
def transition_service_report(service_report: str, status: str):
	doc = _report(service_report, "write")
	if status not in TRANSITIONS.get(doc.status, set()):
		frappe.throw(_("Invalid Service Report transition from {0} to {1}.").format(doc.status, status))
	if status == "Customer Signed" and not (doc.customer_signature or (doc.signature_refused and doc.refusal_reason)):
		frappe.throw(_("Capture the customer signature or refusal before continuing."))
	if status in {"Verified", "Submitted"}:
		require_job_access(doc.service_job, "write", manager_only=True)
	old = doc.status
	doc.status = status
	if status == "Generated":
		doc.generated_on = now_datetime()
	if status == "Verified":
		doc.verified_on = now_datetime()
	if status == "Submitted":
		doc.submitted_on = now_datetime()
	doc.flags.fsm_command = True
	doc.flags.ignore_permissions = True
	doc.save()
	append_event("ServiceReportStatusChanged", doc, from_status=old, to_status=status, source="Console")
	return doc.as_dict()


@frappe.whitelist()
def revise_service_report(service_report: str, generation_key: str):
	source = _report(service_report, "write")
	if source.status != "Submitted":
		frappe.throw(_("Only a Submitted report can be revised."))
	result = generate_service_report(source.service_job, source.report_type, generation_key)
	doc = frappe.get_doc("Service Report", result.name)
	if not doc.supersedes:
		doc.supersedes = source.name
		doc.flags.fsm_command = True
		doc.save()
	return doc.as_dict()


@frappe.whitelist()
def issue_service_certificate(service_report: str, certificate_type: str, installed_equipment: str | None = None, generation_key: str | None = None):
	report = _report(service_report, "write")
	require_job_access(report.service_job, "write", manager_only=True)
	if report.status != "Submitted":
		frappe.throw(_("Certificates require a Submitted Service Report."))
	if certificate_type not in CERTIFICATE_TYPES:
		frappe.throw(_("Unsupported certificate type."))
	job = frappe.get_doc("Service Job", report.service_job)
	if installed_equipment and not any(row.installed_equipment == installed_equipment for row in job.equipment):
		frappe.throw(_("Installed Equipment must be linked to the Service Job."))
	key = generation_key or f"{report.name}:{certificate_type}:{installed_equipment or 'job'}"
	if existing := frappe.db.get_value("Service Certificate", {"generation_key": key}, "name"):
		return frappe.get_doc("Service Certificate", existing).as_dict()
	revision = cint(
		frappe.db.get_value(
			"Service Certificate",
			{
				"service_job": job.name,
				"certificate_type": certificate_type,
				"installed_equipment": installed_equipment,
			},
			"revision",
			order_by="revision desc",
		)
	) + 1
	doc = frappe.get_doc({"doctype": "Service Certificate", "service_report": report.name, "service_job": job.name, "installed_equipment": installed_equipment, "certificate_type": certificate_type, "revision": revision, "generation_key": key, "status": "Issued", "customer": report.customer, "company": report.company, "customer_site": report.customer_site, "issued_on": now_datetime(), "snapshot": report.snapshot})
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	append_event("ServiceCertificateIssued", doc, to_status="Issued", source="Console", metadata={"type": certificate_type, "revision": revision})
	return doc.as_dict()


@frappe.whitelist()
def revoke_service_certificate(service_certificate: str, reason: str):
	doc = _certificate(service_certificate, "write")
	require_job_access(doc.service_job, "write", manager_only=True)
	if doc.status != "Issued" or not reason:
		frappe.throw(_("An issued certificate and revocation reason are required."))
	doc.status, doc.revoked_on, doc.revocation_reason = "Revoked", now_datetime(), reason
	doc.flags.fsm_command = True
	doc.save()
	append_event("ServiceCertificateRevoked", doc, from_status="Issued", to_status="Revoked", source="Console", metadata={"reason": reason})
	return doc.as_dict()


@frappe.whitelist()
def list_service_documents(service_job: str):
	require_job_access(service_job, "read")
	return {"reports": frappe.get_list("Service Report", filters={"service_job": service_job}, fields=["name", "report_type", "revision", "status", "generated_on", "submitted_on", "modified"], order_by="revision desc"), "certificates": frappe.get_list("Service Certificate", filters={"service_job": service_job}, fields=["name", "certificate_type", "installed_equipment", "revision", "status", "issued_on", "modified"], order_by="issued_on desc")}


@frappe.whitelist()
def get_service_report(service_report: str):
	return _report(service_report).as_dict()


@frappe.whitelist()
def get_service_certificate(service_certificate: str):
	return _certificate(service_certificate).as_dict()
