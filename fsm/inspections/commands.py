from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime

from fsm.inspections.access import require_inspection_access, require_template_access
from fsm.inspections.outcome_engine import evaluate_inspection
from fsm.security.policy import require_job_access, require_manager_scope, validate_allowed_fields
from fsm.security.scopes import FSM_MANAGER, SYSTEM_MANAGER, current_technician, user_roles

TEMPLATE_FIELDS = {"template_name", "company", "item_group", "description", "items"}
RESULT_FIELDS = {"response_value", "numeric_value", "date_value", "attachment", "signature", "evidence"}
TEMPLATE_TRANSITIONS = {
	"Draft": {"Active", "Archived"},
	"Active": {"Inactive", "Archived"},
	"Inactive": {"Active", "Archived"},
	"Archived": set(),
}


def _result(doc):
	return frappe.get_doc(doc.doctype, doc.name).as_dict()


@frappe.whitelist()
def create_template(**values):
	validate_allowed_fields(values, TEMPLATE_FIELDS)
	require_manager_scope(values.get("company"))
	doc = frappe.get_doc({"doctype": "Inspection Template", "status": "Draft", **values})
	doc.flags.fsm_inspection_command = True
	doc.insert()
	return _result(doc)


@frappe.whitelist()
def update_template(inspection_template: str, **values):
	validate_allowed_fields(values, TEMPLATE_FIELDS - {"company"})
	doc = require_template_access(inspection_template, "write")
	if doc.status == "Archived":
		frappe.throw(_("An archived Inspection Template cannot be edited."))
	doc.update(values)
	doc.flags.fsm_inspection_command = True
	doc.save()
	return _result(doc)


@frappe.whitelist()
def transition_template(inspection_template: str, status: str):
	doc = require_template_access(inspection_template, "write")
	if status not in TEMPLATE_TRANSITIONS.get(doc.status, set()):
		frappe.throw(_("Illegal Inspection Template transition."))
	doc.flags.fsm_inspection_command = True
	doc.status = status
	doc.save()
	return _result(doc)


@frappe.whitelist()
def start_inspection(
	service_job: str,
	installed_equipment: str,
	inspection_template: str,
	service_visit: str | None = None,
	technician: str | None = None,
):
	job = require_job_access(service_job, "write")
	template = require_template_access(inspection_template, "read")
	if template.status != "Active" or template.company != job.company:
		frappe.throw(_("Select an active Inspection Template for the Job Company."), frappe.ValidationError)
	roles = user_roles()
	if {FSM_MANAGER, SYSTEM_MANAGER} & roles:
		technician = technician or job.primary_technician
		if not technician or frappe.db.get_value("Technician", technician, "company") != job.company:
			frappe.throw(_("Select a Technician from the Job Company."), frappe.ValidationError)
	else:
		technician = current_technician()
	equipment = frappe.get_cached_doc("Installed Equipment", installed_equipment)
	doc = frappe.get_doc(
		{
			"doctype": "Equipment Inspection",
			"installed_equipment": installed_equipment,
			"service_job": job.name,
			"service_visit": service_visit,
			"inspection_template": template.name,
			"template_revision": template.revision,
			"technician": technician,
			"customer": job.customer,
			"company": job.company,
			"customer_site": equipment.customer_site,
			"status": "In Progress",
			"overall_result": "Pending",
			"started_on": now_datetime(),
		}
	)
	for item in template.items:
		doc.append(
			"results",
			{
				"template_item": item.name,
				"item_code": item.code,
				"label": item.label,
				"response_type": item.response_type,
				"required": item.required,
				"min_value": item.min_value,
				"max_value": item.max_value,
				"options": item.options,
				"measurement_unit": item.measurement_unit,
				"evidence_required": item.evidence_required,
				"failure_severity": item.failure_severity,
				"action_hint": item.action_on_fail,
			},
		)
	doc.flags.fsm_inspection_command = True
	doc.insert(ignore_permissions=True)
	return _result(doc)


@frappe.whitelist()
def save_inspection_responses(inspection: str, responses):
	doc = require_inspection_access(inspection, "write")
	if doc.status != "In Progress":
		frappe.throw(_("Only an in-progress Inspection can accept responses."))
	responses = frappe.parse_json(responses) if isinstance(responses, str) else responses
	by_code = {row.item_code: row for row in doc.results}
	for response in responses or []:
		code = response.get("item_code")
		if code not in by_code:
			frappe.throw(_("Unknown Inspection item code: {0}").format(code), frappe.ValidationError)
		validate_allowed_fields(
			{key: value for key, value in response.items() if key != "item_code"}, RESULT_FIELDS
		)
		row = by_code[code]
		for field in RESULT_FIELDS:
			if field in response:
				row.set(field, response[field])
		row.responded = 1
	doc.flags.fsm_inspection_command = True
	doc.save()
	return _result(doc)


@frappe.whitelist()
def complete_inspection(inspection: str):
	doc = require_inspection_access(inspection, "write")
	if doc.status != "In Progress":
		frappe.throw(_("Only an in-progress Inspection can be completed."))
	outcome = evaluate_inspection(doc)
	if not outcome.valid:
		frappe.throw("; ".join(outcome.errors), frappe.ValidationError)
	doc.flags.fsm_inspection_command = True
	doc.status = "Completed"
	doc.overall_result = outcome.overall_result
	doc.corrective_action_hint = outcome.corrective_action_hint
	doc.completed_on = now_datetime()
	doc.save()
	return _result(doc)


@frappe.whitelist()
def close_inspection_without_access(inspection: str, result: str, reason: str):
	doc = require_inspection_access(inspection, "write")
	if result not in {"Not Accessible", "Skipped"} or not (reason or "").strip():
		frappe.throw(_("Use Not Accessible or Skipped and provide a reason."), frappe.ValidationError)
	if doc.status != "In Progress":
		frappe.throw(_("Only an in-progress Inspection can be closed."))
	doc.flags.fsm_inspection_command = True
	doc.status = "Completed"
	doc.overall_result = result
	doc.corrective_action_hint = reason.strip()
	doc.completed_on = now_datetime()
	doc.save()
	return _result(doc)
