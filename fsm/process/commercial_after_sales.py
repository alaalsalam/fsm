from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_years, cint

from fsm.security.policy import require_manager_scope
from fsm.service_operations.events import append_event

DEFAULT_SERVICE_TYPE = "Preventive Maintenance"
DEFAULT_INTERVAL_COUNT = 3
DEFAULT_INTERVAL_UNIT = "Months"


def _serviceable_item_codes(doc) -> set[str]:
	item_codes = {row.item_code for row in doc.items if row.item_code}
	if not item_codes:
		return set()
	return set(
		frappe.get_all(
			"Item",
			filters={"name": ["in", sorted(item_codes)], "fsm_serviceable": 1},
			pluck="name",
			limit=len(item_codes),
		)
	)


def _common_reference(doc, *fieldnames: str) -> str | None:
	values = {row.get(fieldname) for row in doc.items for fieldname in fieldnames if row.get(fieldname)}
	return next(iter(values)) if len(values) == 1 else None


def _automation_key(doc) -> str:
	sales_order = _common_reference(doc, "sales_order", "against_sales_order")
	if sales_order:
		return f"sales-order:{sales_order}"
	if doc.doctype == "Sales Invoice":
		delivery_note = _common_reference(doc, "delivery_note")
		if delivery_note:
			return f"delivery_note:{delivery_note}"
	if doc.doctype == "Delivery Note":
		sales_invoice = _common_reference(doc, "against_sales_invoice")
		if sales_invoice:
			return f"sales-invoice:{sales_invoice}"
	return f"{frappe.scrub(doc.doctype)}:{doc.name}"


def _source_values(doc) -> dict:
	values = {
		"customer": doc.customer,
		"company": doc.company,
		"project": doc.get("project"),
		"sales_order": _common_reference(doc, "sales_order", "against_sales_order"),
	}
	if doc.doctype == "Sales Invoice":
		values["sales_invoice"] = doc.name
		values["delivery_note"] = _common_reference(doc, "delivery_note")
	else:
		values["delivery_note"] = doc.name
		values["sales_invoice"] = _common_reference(doc, "against_sales_invoice")
	return values


def _scope_for_delivery(delivery_note: str) -> list[dict]:
	return [
		{
			"customer_site": row.customer_site,
			"installed_equipment": row.name,
			"active": 1,
		}
		for row in frappe.get_all(
			"Installed Equipment",
			filters={
				"delivery_note": delivery_note,
				"customer_site": ["is", "set"],
				"status": ["not in", ["Returned", "Replaced", "Disposed"]],
			},
			fields=["name", "customer_site"],
			order_by="creation asc",
			limit=10000,
		)
	]


def _link_source(doc, contract_name: str) -> None:
	fieldname = "fsm_service_contract"
	if frappe.get_meta(doc.doctype).has_field(fieldname):
		frappe.db.set_value(doc.doctype, doc.name, fieldname, contract_name, update_modified=False)


def _merge_source_and_scope(contract, doc) -> None:
	changed = False
	for fieldname, value in _source_values(doc).items():
		if value and not contract.get(fieldname):
			contract.set(fieldname, value)
			changed = True
	if doc.doctype == "Delivery Note" and contract.status == "Draft":
		existing = {row.installed_equipment for row in contract.covered_equipment if row.installed_equipment}
		for row in _scope_for_delivery(doc.name):
			if row["installed_equipment"] not in existing:
				contract.append("covered_equipment", row)
				existing.add(row["installed_equipment"])
				changed = True
	if changed:
		contract.flags.fsm_command = True
		contract.save(ignore_permissions=True)
	_link_source(doc, contract.name)


def ensure_contract_from_commercial_document(doc, *, system_operation: bool = False):
	"""Create or reuse one reviewable draft contract for a submitted commercial source.

	This is an internal document-event operation. Its authorization boundary is the
	submitted ERPNext source document; the whitelisted retry command performs an
	explicit manager/company guard before entering this function.
	"""
	if doc.docstatus != 1 or cint(doc.get("is_return")) or doc.get("fsm_service_job"):
		return None
	if not system_operation:
		require_manager_scope(doc.company)
	if not _serviceable_item_codes(doc):
		return None

	key = _automation_key(doc)
	existing = frappe.db.get_value("Service Contract", {"automation_key": key}, "name")
	if existing:
		contract = frappe.get_doc("Service Contract", existing)
		_merge_source_and_scope(contract, doc)
		return contract

	start_date = doc.get("posting_date")
	values = _source_values(doc)
	contract = frappe.get_doc(
		{
			"doctype": "Service Contract",
			"status": "Draft",
			"automation_key": key,
			**values,
			"start_date": start_date,
			"end_date": add_years(start_date, 1),
			"included_visits": 4,
			"response_sla_hours": 4,
			"resolution_sla_hours": 24,
			"maintenance_service_type": DEFAULT_SERVICE_TYPE,
			"maintenance_interval_count": DEFAULT_INTERVAL_COUNT,
			"maintenance_interval_unit": DEFAULT_INTERVAL_UNIT,
			"first_maintenance_date": start_date,
			"covered_equipment": _scope_for_delivery(doc.name) if doc.doctype == "Delivery Note" else [],
			"coverage_rules": [
				{
					"rule_name": "Standard Preventive Maintenance",
					"service_type": DEFAULT_SERVICE_TYPE,
					"classification": "Contract Covered",
					"labour": 1,
					"parts": 0,
					"travel": 1,
					"inspection": 1,
					"active": 1,
				}
			],
			"entitlements": [
				{
					"entitlement_type": "Visit",
					"service_type": DEFAULT_SERVICE_TYPE,
					"included_quantity": 4,
					"period_start": start_date,
					"period_end": add_years(start_date, 1),
					"active": 1,
				}
			],
			"notes": _(
				"Automatically prepared from submitted {0} {1}. Review scope, terms, and cadence before activation."
			).format(doc.doctype, doc.name),
		}
	)
	contract.flags.fsm_command = True
	try:
		contract.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		winner = frappe.db.get_value("Service Contract", {"automation_key": key}, "name")
		if not winner:
			raise
		contract = frappe.get_doc("Service Contract", winner)
		_merge_source_and_scope(contract, doc)
		return contract

	_link_source(doc, contract.name)
	append_event(
		"ServiceContractDraftedFromSale",
		contract,
		to_status="Draft",
		source="System",
		correlation_id=doc.name,
		metadata={"source_doctype": doc.doctype, "source_name": doc.name},
	)
	return contract


def on_sales_invoice_submit(doc, method=None):
	ensure_contract_from_commercial_document(doc, system_operation=True)


def on_delivery_note_submit(doc, method=None):
	ensure_contract_from_commercial_document(doc, system_operation=True)


def sync_delivery_contract_scope(delivery_note: str, *, system_operation: bool = False):
	doc = frappe.get_doc("Delivery Note", delivery_note)
	if doc.docstatus != 1:
		frappe.throw(_("After-sales setup requires a submitted Delivery Note."), frappe.ValidationError)
	if not system_operation:
		require_manager_scope(doc.company)
	contract = ensure_contract_from_commercial_document(doc, system_operation=True)
	return contract.as_dict() if contract else None


@frappe.whitelist()
def retry_contract_from_delivery(delivery_note: str):
	return sync_delivery_contract_scope(delivery_note)
