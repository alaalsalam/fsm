from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from fsm.inspections.commands import create_template, transition_template
from fsm.installed_base.access import require_equipment_access
from fsm.security.policy import require_job_access, require_manager_scope, validate_allowed_fields
from fsm.service_operations.events import append_event

PROFILE_FIELDS = {
	"equipment_category",
	"extinguisher_type",
	"capacity",
	"capacity_uom",
	"agent_type",
	"fire_manufacturer",
	"fire_model",
	"manufacturing_date",
	"expiry_date",
	"pressure_rating",
	"hydro_test_interval_months",
}


def _result(doc):
	return frappe.get_doc(doc.doctype, doc.name).as_dict()


@frappe.whitelist()
def update_fire_safety_profile(installed_equipment: str, **values):
	validate_allowed_fields(values, PROFILE_FIELDS)
	doc = require_equipment_access(installed_equipment, "write", manager_only=True)
	doc.update(values)
	doc.flags.fsm_command = True
	doc.save()
	append_event("FireSafetyProfileUpdated", doc, source="Console", metadata={"fields": sorted(values)})
	return _result(doc)


@frappe.whitelist()
def record_extinguisher_service(
	service_job: str,
	installed_equipment: str,
	service_visit: str | None = None,
	refill_date: str | None = None,
	refill_result: str | None = None,
	hydro_test_date: str | None = None,
):
	job = require_job_access(service_job, "write")
	doc = require_equipment_access(installed_equipment, "read")
	if not any(row.installed_equipment == doc.name for row in job.equipment):
		frappe.throw(_("Equipment must be linked to the Service Job."), frappe.ValidationError)
	if doc.equipment_category != "Fire Extinguisher":
		frappe.throw(_("This command applies only to Fire Extinguishers."), frappe.ValidationError)
	if service_visit and frappe.db.get_value("Service Visit", service_visit, "service_job") != job.name:
		frappe.throw(_("Service Visit must belong to the Service Job."), frappe.ValidationError)
	if refill_result and refill_result not in {"Completed", "Failed", "Not Required"}:
		frappe.throw(_("Invalid refill result."), frappe.ValidationError)
	if not refill_date and not hydro_test_date:
		frappe.throw(_("Record a refill date or hydro test date."), frappe.ValidationError)
	doc.flags.fsm_command = True
	if refill_date:
		doc.last_refill_date = getdate(refill_date)
		doc.last_refill_result = refill_result or "Completed"
	if hydro_test_date:
		doc.last_hydro_test_date = getdate(hydro_test_date)
	doc.save(ignore_permissions=True)
	append_event(
		"FireExtinguisherServiceRecorded",
		doc,
		source="Mobile",
		metadata={
			"service_job": job.name,
			"service_visit": service_visit,
			"refill_date": refill_date,
			"refill_result": refill_result,
			"hydro_test_date": hydro_test_date,
			"hydro_due_date": doc.hydro_due_date,
		},
	)
	return _result(doc)


@frappe.whitelist()
def install_standard_extinguisher_template(company: str):
	require_manager_scope(company)
	name = frappe.db.get_value(
		"Inspection Template", {"company": company, "template_name": "Standard Fire Extinguisher Inspection"}
	)
	if name:
		return frappe.get_doc("Inspection Template", name).as_dict()
	items = _standard_items()
	doc = create_template(
		template_name="Standard Fire Extinguisher Inspection",
		company=company,
		description="Configurable baseline inspection for portable fire extinguishers.",
		items=items,
	)
	return transition_template(doc.name, "Active")


def _standard_items():
	definitions = [
		("BODY", "Cylinder / body condition", "Pass/Fail", "Repair", 1),
		("CORROSION", "No corrosion", "Pass/Fail", "Replace", 1),
		("PRESSURE", "Pressure within range", "Measurement", "Refill", 1),
		("HOSE", "Hose condition", "Pass/Fail", "Repair", 0),
		("NOZZLE", "Nozzle condition", "Pass/Fail", "Repair", 0),
		("VALVE", "Valve condition", "Pass/Fail", "Repair", 0),
		("PIN", "Safety pin present", "Yes/No", "Repair", 0),
		("SEAL", "Tamper seal intact", "Yes/No", "Repair", 0),
		("LABEL", "Label legible", "Pass/Fail", "Repair", 0),
		("MOUNTING", "Mounting secure", "Pass/Fail", "Repair", 0),
		("ACCESS", "Accessible", "Yes/No", "Follow Up", 1),
		("SIGNAGE", "Signage visible", "Pass/Fail", "Follow Up", 0),
		("WEIGHT", "Measured weight", "Measurement", "Refill", 0),
		("MFG_DATE", "Manufacturing date", "Date", "Follow Up", 0),
		("EXPIRY", "Expiry date", "Date", "Replace", 0),
		("LAST_REFILL", "Last refill date", "Date", "Refill", 0),
		("HYDRO", "Last hydro test date", "Date", "Follow Up", 0),
		("PHOTOS", "Equipment photos", "Photo", "Follow Up", 1),
		("NOTES", "Inspector notes", "Text", "None", 0),
	]
	return [
		{
			"code": code,
			"label": label,
			"response_type": response_type,
			"required": int(code not in {"WEIGHT", "NOTES"}),
			"measurement_unit": "bar" if code == "PRESSURE" else ("kg" if code == "WEIGHT" else None),
			"evidence_required": evidence,
			"failure_severity": "Critical"
			if code in {"BODY", "CORROSION", "PRESSURE", "EXPIRY"}
			else "Major",
			"action_on_fail": action,
		}
		for code, label, response_type, action, evidence in definitions
	]
