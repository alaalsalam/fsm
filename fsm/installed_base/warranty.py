from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate, nowdate


def warranty_start_for(doc):
	basis = frappe.db.get_single_value("Service Settings", "warranty_start_basis") or "Delivery Date"
	return {
		"Delivery Date": doc.delivery_date,
		"Installation Date": doc.installation_date,
		"Commissioning Date": doc.commissioning_date,
	}.get(basis)


def warranty_status_for(warranty_end_date) -> str:
	"""Pure status computation — callers that already hold warranty_end_date
	(list rows) must use this instead of loading a full document per row."""
	if not warranty_end_date:
		return "Not Applicable"
	return "Active" if getdate(warranty_end_date) >= getdate(nowdate()) else "Expired"


def get_equipment_warranty_status(equipment) -> str:
	doc = (
		equipment if getattr(equipment, "doctype", None) else frappe.get_doc("Installed Equipment", equipment)
	)
	return warranty_status_for(doc.warranty_end_date)


def apply_warranty_projection(doc) -> None:
	days = int(frappe.db.get_value("Item", doc.item_code, "fsm_default_warranty_days") or 0)
	start = warranty_start_for(doc)
	if days > 0 and start:
		doc.warranty_start_date = start
		doc.warranty_end_date = add_days(start, days)
	else:
		doc.warranty_start_date = None
		doc.warranty_end_date = None
	doc.warranty_status = get_equipment_warranty_status(doc)
