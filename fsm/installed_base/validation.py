from __future__ import annotations

import frappe
from frappe import _

from fsm.security.policy import require_manager_scope


def dynamic_link_exists(parenttype: str, parent: str, link_doctype: str, link_name: str) -> bool:
	return bool(
		frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": parenttype,
				"parent": parent,
				"link_doctype": link_doctype,
				"link_name": link_name,
			},
		)
	)


def address_belongs_to_customer(address: str, customer: str) -> bool:
	return dynamic_link_exists("Address", address, "Customer", customer)


def contact_belongs_to_customer(contact: str, customer: str) -> bool:
	return dynamic_link_exists("Contact", contact, "Customer", customer)


def validate_customer_address(
	customer: str,
	address: str | None,
	override_reason: str | None,
	company: str,
	territory: str | None,
) -> None:
	if not address or address_belongs_to_customer(address, customer):
		return
	if not (override_reason or "").strip():
		frappe.throw(_("Address is not linked to this Customer. A Manager override reason is required."))
	require_manager_scope(company, territory)


def validate_equipment_links(doc) -> None:
	item = frappe.get_cached_doc("Item", doc.item_code)
	if not item.get("fsm_serviceable"):
		frappe.throw(_("Item {0} is not enabled for FSM after-sales service.").format(doc.item_code))
	tracking_mode = item.get("fsm_tracking_mode") or "None"
	if (item.has_serial_no or tracking_mode == "Serial") and not doc.serial_no:
		frappe.throw(_("A canonical ERPNext Serial No is required for this Item."))
	if doc.serial_no:
		serial_item = frappe.db.get_value("Serial No", doc.serial_no, "item_code")
		if not serial_item:
			frappe.throw(_("Serial No does not exist in ERPNext."))
		if serial_item != doc.item_code:
			frappe.throw(_("Serial No belongs to a different Item."))
		existing = frappe.db.get_value(
			"Installed Equipment", {"serial_no": doc.serial_no, "name": ("!=", doc.name)}, "name"
		)
		if existing:
			frappe.throw(_("Serial No is already registered as Installed Equipment {0}.").format(existing))
	if doc.batch_no:
		batch_item = frappe.db.get_value("Batch", doc.batch_no, "item")
		if batch_item and batch_item != doc.item_code:
			frappe.throw(_("Batch belongs to a different Item."))
	if doc.customer_site:
		site = frappe.get_cached_doc("Customer Site", doc.customer_site)
		if site.customer != doc.customer or site.company != doc.company:
			frappe.throw(_("Customer Site must belong to the Equipment Customer and Company."))
	if doc.equipment_location:
		location_site = frappe.db.get_value("Equipment Location", doc.equipment_location, "customer_site")
		if not doc.customer_site or location_site != doc.customer_site:
			frappe.throw(_("Equipment Location must belong to the selected Customer Site."))
	if (doc.installed_quantity or 0) <= 0:
		frappe.throw(_("Installed Quantity must be greater than zero."))
