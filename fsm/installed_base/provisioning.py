from __future__ import annotations

import hashlib
import math

import frappe
from frappe import _

from fsm.security.policy import require_manager_scope
from fsm.service_operations.events import append_event


def _key(delivery_note: str, row_name: str, identity: str) -> str:
	return hashlib.sha256(f"{delivery_note}:{row_name}:{identity}".encode()).hexdigest()


def _serials(value: str | None) -> list[str]:
	return [part.strip() for part in (value or "").replace(",", "\n").splitlines() if part.strip()]


def _bundle_entries(row) -> list[frappe._dict]:
	bundle = row.get("serial_and_batch_bundle")
	if not bundle:
		return []
	return frappe.get_all(
		"Serial and Batch Entry",
		filters={"parent": bundle, "parenttype": "Serial and Batch Bundle"},
		fields=["serial_no", "batch_no", "qty"],
		order_by="idx asc",
	)


def _row_serials(row) -> list[str]:
	serials = _serials(row.get("serial_no"))
	return serials or [entry.serial_no for entry in _bundle_entries(row) if entry.serial_no]


def _row_batch(row) -> str | None:
	if row.get("batch_no"):
		return row.batch_no
	return next((entry.batch_no for entry in _bundle_entries(row) if entry.batch_no), None)


def _site_for_delivery(doc) -> str | None:
	address = doc.get("shipping_address_name") or doc.get("customer_address")
	if not address:
		return None
	return frappe.db.get_value(
		"Customer Site",
		{"customer": doc.customer, "company": doc.company, "address": address, "enabled": 1},
		"name",
	)


def _identities(row, tracking_mode: str) -> list[tuple[str, str | None, float]]:
	if tracking_mode == "Serial":
		serials = _row_serials(row)
		if len(serials) != int(abs(row.qty)):
			frappe.throw(_("Delivery row {0} requires one Serial No per delivered unit.").format(row.idx))
		return [(f"SERIAL:{serial}", serial, 1) for serial in serials]
	if tracking_mode == "Unit":
		quantity = abs(float(row.qty))
		if not quantity.is_integer():
			frappe.throw(_("Unit-tracked Item quantity must be a whole number."))
		return [(f"UNIT:{sequence:06d}", None, 1) for sequence in range(1, int(quantity) + 1)]
	if tracking_mode == "Quantity":
		return [("QUANTITY", None, abs(float(row.qty)))]
	return []


def _provision_delivery_note(delivery_note, *, system_operation=False):
	doc = (
		delivery_note
		if getattr(delivery_note, "doctype", None)
		else frappe.get_doc("Delivery Note", delivery_note)
	)
	if doc.docstatus != 1 or doc.is_return:
		frappe.throw(_("Only a submitted non-return Delivery Note can be provisioned."))
	if not system_operation:
		require_manager_scope(doc.company)
	created = []
	existing = []
	site = _site_for_delivery(doc)
	for row in doc.items:
		item = frappe.get_cached_doc("Item", row.item_code)
		if not item.get("fsm_serviceable") or not item.get("fsm_create_installed_equipment"):
			continue
		mode = item.get("fsm_tracking_mode") or ("Serial" if item.has_serial_no else "None")
		for identity, serial_no, quantity in _identities(row, mode):
			provisioning_key = _key(doc.name, row.name, identity)
			found = frappe.db.get_value("Installed Equipment", {"provisioning_key": provisioning_key}, "name")
			if found:
				existing.append(found)
				continue
			status = "Active" if item.get("fsm_activation_on_delivery") else "Pending Installation"
			equipment = frappe.get_doc(
				{
					"doctype": "Installed Equipment",
					"equipment_name": item.item_name,
					"status": status,
					"company": doc.company,
					"customer": doc.customer,
					"customer_site": site,
					"item_code": row.item_code,
					"serial_no": serial_no,
					"batch_no": _row_batch(row),
					"installed_quantity": quantity,
					"sales_order": row.get("against_sales_order"),
					"sales_order_item": row.get("so_detail"),
					"delivery_note": doc.name,
					"delivery_note_item": row.name,
					"sales_invoice": row.get("against_sales_invoice"),
					"delivery_date": doc.posting_date,
					"source": "Delivery Note",
					"provisioning_key": provisioning_key,
				}
			)
			equipment.flags.fsm_command = True
			try:
				equipment.insert(ignore_permissions=True)
			except frappe.DuplicateEntryError:
				found = frappe.db.get_value(
					"Installed Equipment", {"provisioning_key": provisioning_key}, "name"
				)
				if not found:
					raise
				existing.append(found)
				continue
			created.append(equipment.name)
			append_event(
				"EquipmentProvisioned",
				equipment,
				to_status=status,
				source="System",
				correlation_id=doc.name,
				metadata={"delivery_note": doc.name, "delivery_note_item": row.name, "tracking_mode": mode},
			)
			if status == "Active":
				append_event(
					"EquipmentActivated",
					equipment,
					to_status="Active",
					source="System",
					correlation_id=doc.name,
				)
	count = frappe.db.count("Installed Equipment", {"delivery_note": doc.name})
	frappe.db.set_value(
		"Delivery Note",
		doc.name,
		{"fsm_provisioning_status": "Completed", "fsm_installed_equipment_count": count},
		update_modified=False,
	)
	return {"delivery_note": doc.name, "created": created, "existing": existing, "count": count}


def cancel_delivery_note_equipment(doc) -> list[str]:
	names = frappe.get_all("Installed Equipment", filters={"delivery_note": doc.name}, pluck="name")
	changed = []
	for name in names:
		equipment = frappe.get_doc("Installed Equipment", name)
		if equipment.status in {"Returned", "Replaced", "Disposed"}:
			continue
		old = equipment.status
		equipment.flags.fsm_command = True
		equipment.status = "Inactive"
		equipment.save()
		append_event(
			"DeliveryCancelled",
			equipment,
			from_status=old,
			to_status="Inactive",
			source="System",
			correlation_id=doc.name,
			metadata={"delivery_note": doc.name},
		)
		changed.append(name)
	frappe.db.set_value(
		"Delivery Note", doc.name, "fsm_provisioning_status", "Cancelled", update_modified=False
	)
	return changed


def reconcile_return_delivery_note(doc) -> list[str]:
	if not doc.is_return:
		return []
	changed = []
	for row in doc.items:
		serials = _row_serials(row)
		if serials:
			names = frappe.get_all(
				"Installed Equipment", filters={"serial_no": ("in", serials)}, pluck="name"
			)
		else:
			filters = {
				"customer": doc.customer,
				"item_code": row.item_code,
				"status": ("not in", ["Returned", "Disposed"]),
			}
			if doc.return_against:
				filters["delivery_note"] = doc.return_against
			names = frappe.get_all(
				"Installed Equipment",
				filters=filters,
				pluck="name",
				order_by="creation asc",
				limit=max(1, math.ceil(abs(float(row.qty)))),
			)
		for name in names:
			equipment = frappe.get_doc("Installed Equipment", name)
			old = equipment.status
			equipment.flags.fsm_command = True
			equipment.status = "Returned"
			equipment.save()
			append_event(
				"EquipmentReturned",
				equipment,
				from_status=old,
				to_status="Returned",
				source="System",
				correlation_id=doc.name,
				metadata={"return_delivery_note": doc.name, "return_against": doc.return_against},
			)
			changed.append(name)
	frappe.db.set_value(
		"Delivery Note",
		doc.name,
		{"fsm_provisioning_status": "Return Reconciled", "fsm_installed_equipment_count": len(changed)},
		update_modified=False,
	)
	return changed


def on_delivery_note_submit(doc, method=None):
	if doc.is_return:
		reconcile_return_delivery_note(doc)
	else:
		_provision_delivery_note(doc, system_operation=True)


def on_delivery_note_cancel(doc, method=None):
	if not doc.is_return:
		cancel_delivery_note_equipment(doc)


@frappe.whitelist()
def provision_delivery_note(delivery_note: str):
	"""Explicit, authorized retry command for a submitted Delivery Note."""
	return _provision_delivery_note(delivery_note)


@frappe.whitelist()
def reconcile_delivery_note_provisioning(delivery_note: str):
	doc = frappe.get_doc("Delivery Note", delivery_note)
	require_manager_scope(doc.company)
	if doc.is_return:
		return {"delivery_note": doc.name, "returned": reconcile_return_delivery_note(doc)}
	return _provision_delivery_note(doc, system_operation=True)
