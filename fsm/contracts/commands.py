from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

from fsm.contracts.access import require_contract_access
from fsm.contracts.coverage_engine import evaluate_coverage
from fsm.security.policy import require_job_access, require_manager_scope, validate_allowed_fields
from fsm.service_operations.events import append_event

CONTRACT_FIELDS = {
	"customer",
	"company",
	"project",
	"start_date",
	"end_date",
	"included_visits",
	"emergency_visits",
	"response_sla_hours",
	"resolution_sla_hours",
	"covered_equipment",
	"coverage_rules",
	"entitlements",
	"quotation",
	"sales_order",
	"sales_invoice",
	"delivery_note",
	"maintenance_service_type",
	"maintenance_interval_count",
	"maintenance_interval_unit",
	"first_maintenance_date",
	"renewal_recommended",
	"renewal_quotation",
	"notes",
}
CONTRACT_UPDATE_FIELDS = CONTRACT_FIELDS - {"customer", "company"}
TRANSITIONS = {
	"Draft": {"Active", "Cancelled"},
	"Active": {"Suspended", "Expired", "Cancelled"},
	"Suspended": {"Active", "Expired", "Cancelled"},
	"Expired": set(),
	"Cancelled": set(),
}
COVERAGE_STATUSES = {
	"Warranty",
	"Contract Covered",
	"Partially Covered",
	"Chargeable",
	"FOC",
	"Not Covered",
}


def _result(doc):
	return frappe.get_doc(doc.doctype, doc.name).as_dict()


@frappe.whitelist()
def create_contract(**values):
	validate_allowed_fields(values, CONTRACT_FIELDS)
	require_manager_scope(values.get("company"))
	doc = frappe.get_doc({"doctype": "Service Contract", "status": "Draft", **values})
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	append_event("ServiceContractCreated", doc, to_status="Draft", source="Console")
	return _result(doc)


@frappe.whitelist()
def update_contract(service_contract: str, **values):
	validate_allowed_fields(values, CONTRACT_UPDATE_FIELDS)
	doc = require_contract_access(service_contract, "write", manager_only=True)
	if doc.status in {"Expired", "Cancelled"}:
		frappe.throw(_("A terminal Service Contract cannot be edited."))
	doc.update(values)
	doc.flags.fsm_command = True
	doc.save()
	return _result(doc)


@frappe.whitelist()
def transition_contract(service_contract: str, status: str, reason: str | None = None, source="API"):
	doc = require_contract_access(service_contract, "write", manager_only=True)
	if status not in TRANSITIONS.get(doc.status, set()):
		frappe.throw(_("Illegal Contract transition from {0} to {1}.").format(doc.status, status))
	previous = doc.status
	if status == "Active" and doc.automation_key:
		_validate_commercial_contract_readiness(doc)
	doc.flags.fsm_command = True
	doc.status = status
	doc.save()
	plans = []
	if status == "Active" and doc.automation_key and doc.maintenance_service_type:
		from fsm.process.maintenance_flow import create_maintenance_plans_from_contract

		result = create_maintenance_plans_from_contract(
			doc.name,
			service_type=doc.maintenance_service_type,
			interval_count=doc.maintenance_interval_count,
			interval_unit=doc.maintenance_interval_unit,
			first_due_date=doc.first_maintenance_date or doc.start_date,
			preview=0,
		)
		plans = result.get("plans") or []
	append_event(
		"ServiceContractStatusChanged",
		doc,
		from_status=previous,
		to_status=status,
		source=source,
		metadata={"reason": reason} if reason else None,
	)
	result = _result(doc)
	result["maintenance_plans"] = plans
	return result


def _validate_commercial_contract_readiness(contract) -> None:
	if not contract.covered_equipment:
		frappe.throw(
			_("Confirm installation and add the delivered equipment to the Contract before activation."),
			frappe.ValidationError,
		)
	if not contract.delivery_note:
		return
	delivered = frappe.get_all(
		"Installed Equipment",
		filters={
			"delivery_note": contract.delivery_note,
			"status": ["not in", ["Returned", "Replaced", "Disposed"]],
		},
		fields=["name", "status", "customer_site"],
		limit=10000,
	)
	pending = [row.name for row in delivered if row.status == "Pending Installation" or not row.customer_site]
	if pending:
		frappe.throw(
			_("Confirm all delivered equipment installations before activating the Contract."),
			frappe.ValidationError,
		)
	covered = {row.installed_equipment for row in contract.covered_equipment if row.installed_equipment}
	missing = [row.name for row in delivered if row.name not in covered]
	if missing:
		frappe.throw(
			_("Synchronize all delivered equipment into the Contract scope before activation."),
			frappe.ValidationError,
		)


@frappe.whitelist()
def renew_contract(service_contract: str, start_date: str, end_date: str):
	old = require_contract_access(service_contract, "write", manager_only=True)
	values = {field: old.get(field) for field in CONTRACT_FIELDS if field not in {"start_date", "end_date"}}
	for table in ("covered_equipment", "coverage_rules", "entitlements"):
		values[table] = []
		for row in old.get(table):
			row_values = row.as_dict(no_nulls=False)
			for field in (
				"name",
				"parent",
				"parentfield",
				"parenttype",
				"doctype",
				"idx",
				"creation",
				"modified",
				"owner",
				"modified_by",
			):
				row_values.pop(field, None)
			if table == "entitlements":
				row_values["used_quantity"] = 0
				row_values["remaining_quantity"] = row_values.get("included_quantity") or 0
				if row_values.get("period_start"):
					row_values["period_start"] = start_date
				if row_values.get("period_end"):
					row_values["period_end"] = end_date
			values[table].append(row_values)
	values.update({"start_date": start_date, "end_date": end_date, "first_maintenance_date": start_date})
	doc = frappe.get_doc({"doctype": "Service Contract", "status": "Draft", **values})
	doc.renewed_from = old.name
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	append_event(
		"ServiceContractRenewalCreated",
		doc,
		to_status="Draft",
		source="Console",
		metadata={"renewed_from": old.name},
	)
	return _result(doc)


@frappe.whitelist()
def classify_job_coverage(
	service_job: str,
	installed_equipment: str | None = None,
	service_type: str | None = None,
	on_date: str | None = None,
):
	job = require_job_access(service_job, "write", manager_only=True)
	decision = evaluate_coverage(job, installed_equipment, service_type, on_date)
	if decision["status"] not in COVERAGE_STATUSES:
		frappe.throw(_("Unsupported coverage classification."), frappe.ValidationError)
	job.flags.fsm_command = True
	job.service_contract = decision["service_contract"]
	job.coverage_status = decision["status"]
	job.coverage_reason = decision["reason"]
	job.covered_labour = cint(decision["covered_labour"])
	job.covered_parts = cint(decision["covered_parts"])
	job.covered_travel = cint(decision["covered_travel"])
	job.save()
	append_event("JobCoverageClassified", job, source="API", metadata=decision)
	return decision


@frappe.whitelist()
def consume_entitlement(
	service_contract: str,
	entitlement_row: str,
	service_job: str,
	idempotency_key: str,
	quantity: float = 1,
	service_visit: str | None = None,
	reason: str | None = None,
):
	contract = require_contract_access(service_contract, "write", manager_only=True)
	job = require_job_access(service_job, "write", manager_only=True)
	if contract.customer != job.customer or contract.company != job.company:
		frappe.throw(
			_("Contract and Service Job must have the same Customer and Company."), frappe.ValidationError
		)
	if service_visit and frappe.db.get_value("Service Visit", service_visit, "service_job") != job.name:
		frappe.throw(_("Service Visit must belong to the Service Job."), frappe.ValidationError)
	quantity = flt(quantity)
	if quantity <= 0:
		frappe.throw(_("Entitlement quantity must be greater than zero."), frappe.ValidationError)
	idempotency_key = (idempotency_key or "").strip()
	if not idempotency_key or len(idempotency_key) > 140:
		frappe.throw(_("A valid idempotency key is required."), frappe.ValidationError)
	existing = frappe.db.get_value("Service Entitlement Consumption", {"idempotency_key": idempotency_key})
	if existing:
		return frappe.get_doc("Service Entitlement Consumption", existing).as_dict()

	frappe.db.sql("select name from `tabService Contract` where name=%s for update", contract.name)
	contract = frappe.get_doc("Service Contract", contract.name)
	existing = frappe.db.sql(
		"select name from `tabService Entitlement Consumption` where idempotency_key=%s for update",
		idempotency_key,
	)
	if existing:
		return frappe.get_doc("Service Entitlement Consumption", existing[0][0]).as_dict()
	entitlement = next((row for row in contract.entitlements if row.name == entitlement_row), None)
	if not entitlement or not entitlement.active:
		frappe.throw(_("The Contract entitlement is missing or inactive."), frappe.ValidationError)
	if flt(entitlement.remaining_quantity) < quantity:
		frappe.throw(
			_("The Contract entitlement does not have enough remaining quantity."), frappe.ValidationError
		)

	entitlement.used_quantity = flt(entitlement.used_quantity) + quantity
	contract.flags.fsm_command = True
	contract.save()
	consumption = frappe.get_doc(
		{
			"doctype": "Service Entitlement Consumption",
			"idempotency_key": idempotency_key,
			"service_contract": contract.name,
			"entitlement_row": entitlement.name,
			"service_job": job.name,
			"service_visit": service_visit,
			"quantity": quantity,
			"consumed_on": now_datetime(),
			"reason": reason,
		}
	)
	consumption.flags.fsm_internal_consumption = True
	consumption.insert(ignore_permissions=True)
	append_event(
		"ContractEntitlementConsumed",
		job,
		source="API",
		correlation_id=idempotency_key,
		metadata={
			"service_contract": contract.name,
			"entitlement_row": entitlement.name,
			"quantity": quantity,
		},
	)
	return consumption.as_dict()
