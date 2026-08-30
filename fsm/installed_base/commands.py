from __future__ import annotations

import uuid

import frappe
from frappe import _
from frappe.utils import nowdate

from fsm.installed_base.access import require_equipment_access, require_location_access, require_site_access
from fsm.security.policy import require_job_access, require_manager_scope, validate_allowed_fields
from fsm.service_operations.events import append_event

SITE_CREATE_FIELDS = {
	"site_name",
	"site_code",
	"customer",
	"company",
	"status",
	"address",
	"territory",
	"address_override_reason",
	"latitude",
	"longitude",
	"geolocation",
	"primary_contact",
	"site_type",
	"access_notes",
	"working_hours",
	"safety_notes",
	"parent_site",
	"is_group",
	"enabled",
	"notes",
}
SITE_UPDATE_FIELDS = SITE_CREATE_FIELDS - {"site_code", "customer", "company"}
LOCATION_FIELDS = {
	"customer_site",
	"location_name",
	"location_code",
	"parent_location",
	"location_type",
	"description",
	"latitude",
	"longitude",
	"active",
}
EQUIPMENT_CREATE_FIELDS = {
	"equipment_name",
	"company",
	"customer",
	"customer_site",
	"equipment_location",
	"item_code",
	"serial_no",
	"batch_no",
	"asset_tag",
	"sales_order",
	"sales_order_item",
	"sales_invoice",
	"delivery_date",
	"manufacturer",
	"model_no",
	"exact_location_notes",
	"equipment_photo",
	"notes",
}

EQUIPMENT_TRANSITIONS = {
	"Pending Installation": {"Active", "Inactive", "Removed", "Returned"},
	"Active": {"Inactive", "Removed", "Returned", "Replaced", "Disposed"},
	"Inactive": {"Active", "Removed", "Returned", "Disposed"},
	"Removed": {"Active", "Returned", "Disposed"},
	"Returned": set(),
	"Replaced": set(),
	"Disposed": set(),
}


def _result(doc):
	return frappe.get_doc(doc.doctype, doc.name).as_dict()


@frappe.whitelist()
def create_customer_site(**values):
	validate_allowed_fields(values, SITE_CREATE_FIELDS)
	require_manager_scope(values.get("company"), values.get("territory"))
	doc = frappe.get_doc({"doctype": "Customer Site", **values})
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	return _result(doc)


@frappe.whitelist()
def update_customer_site(site: str, **values):
	validate_allowed_fields(values, SITE_UPDATE_FIELDS)
	doc = require_site_access(site, "write", manager_only=True)
	doc.update(values)
	doc.flags.fsm_command = True
	doc.save()
	return _result(doc)


@frappe.whitelist()
def create_equipment_location(**values):
	validate_allowed_fields(values, LOCATION_FIELDS)
	require_site_access(values.get("customer_site"), "write", manager_only=True)
	doc = frappe.get_doc({"doctype": "Equipment Location", **values})
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	return _result(doc)


@frappe.whitelist()
def update_equipment_location(location: str, **values):
	validate_allowed_fields(values, LOCATION_FIELDS - {"customer_site"})
	doc = require_location_access(location, "write", manager_only=True)
	doc.update(values)
	doc.flags.fsm_command = True
	doc.save()
	return _result(doc)


@frappe.whitelist()
def create_installed_equipment(**values):
	validate_allowed_fields(values, EQUIPMENT_CREATE_FIELDS)
	require_manager_scope(values.get("company"))
	doc = frappe.get_doc(
		{
			"doctype": "Installed Equipment",
			**values,
			"source": "Manual",
			"status": "Pending Installation",
			"provisioning_key": f"manual:{uuid.uuid4()}",
			"installed_quantity": 1,
		}
	)
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	append_event("EquipmentProvisioned", doc, to_status=doc.status, source="Console")
	return _result(doc)


@frappe.whitelist()
def confirm_installation(
	installed_equipment: str,
	customer_site: str,
	equipment_location: str | None = None,
	installation_date: str | None = None,
	commissioning_date: str | None = None,
):
	doc = require_equipment_access(installed_equipment, "write", manager_only=True)
	if doc.status != "Pending Installation":
		frappe.throw(_("Only Pending Installation equipment can be installed."))
	site = require_site_access(customer_site, "write", manager_only=True)
	if site.customer != doc.customer or site.company != doc.company:
		frappe.throw(_("Installation Site must belong to the Equipment Customer and Company."))
	if equipment_location:
		location = require_location_access(equipment_location, "read")
		if location.customer_site != site.name:
			frappe.throw(_("Equipment Location must belong to the Installation Site."))
	doc.flags.fsm_command = True
	doc.customer_site = site.name
	doc.equipment_location = equipment_location
	doc.installation_date = installation_date or nowdate()
	doc.commissioning_date = commissioning_date
	old = doc.status
	doc.status = "Active"
	doc.save()
	append_event("InstallationConfirmed", doc, from_status=old, to_status="Active", source="Console")
	append_event("EquipmentActivated", doc, from_status=old, to_status="Active", source="System")
	if doc.delivery_note:
		from fsm.process.commercial_after_sales import sync_delivery_contract_scope

		sync_delivery_contract_scope(doc.delivery_note, system_operation=True)
	return _result(doc)


@frappe.whitelist()
def move_equipment_location(
	installed_equipment: str,
	customer_site: str,
	equipment_location: str | None = None,
	notes: str | None = None,
):
	doc = require_equipment_access(installed_equipment, "write", manager_only=True)
	site = require_site_access(customer_site, "write", manager_only=True)
	if site.customer != doc.customer or site.company != doc.company:
		frappe.throw(_("Destination Site must belong to the Equipment Customer and Company."))
	if equipment_location:
		location = require_location_access(equipment_location, "read")
		if location.customer_site != site.name:
			frappe.throw(_("Equipment Location must belong to the Destination Site."))
	previous = {"customer_site": doc.customer_site, "equipment_location": doc.equipment_location}
	doc.flags.fsm_command = True
	doc.customer_site = site.name
	doc.equipment_location = equipment_location
	doc.exact_location_notes = notes or doc.exact_location_notes
	doc.save()
	append_event(
		"EquipmentMoved",
		doc,
		source="Console",
		metadata={
			"from": previous,
			"to": {"customer_site": site.name, "equipment_location": equipment_location},
		},
	)
	return _result(doc)


@frappe.whitelist()
def change_equipment_status(installed_equipment: str, status: str, reason: str | None = None):
	doc = require_equipment_access(installed_equipment, "write", manager_only=True)
	if status not in EQUIPMENT_TRANSITIONS.get(doc.status, set()):
		frappe.throw(_("Illegal equipment transition from {0} to {1}.").format(doc.status, status))
	old = doc.status
	doc.flags.fsm_command = True
	doc.status = status
	doc.save()
	event = {
		"Active": "EquipmentActivated",
		"Inactive": "EquipmentDeactivated",
		"Returned": "EquipmentReturned",
	}.get(status, "EquipmentStatusChanged")
	append_event(event, doc, from_status=old, to_status=status, source="Console", metadata={"reason": reason})
	return _result(doc)


@frappe.whitelist()
def link_equipment_to_job(
	job: str, installed_equipment: str, service_scope: str | None = None, notes: str | None = None
):
	job_doc = require_job_access(job, "write", manager_only=True)
	equipment = require_equipment_access(installed_equipment, "read", manager_only=True)
	if equipment.customer != job_doc.customer or equipment.company != job_doc.company:
		frappe.throw(_("Equipment must belong to the Job Customer and Company."))
	if equipment.status in {"Returned", "Replaced", "Disposed"}:
		frappe.throw(_("Terminal equipment cannot be linked to new Service Jobs."))
	if any(row.installed_equipment == equipment.name for row in job_doc.equipment):
		frappe.throw(_("Equipment is already linked to this Service Job."))
	job_doc.append(
		"equipment",
		{
			"installed_equipment": equipment.name,
			"service_scope": service_scope,
			"notes": notes,
		},
	)
	job_doc.save()
	append_event("EquipmentLinkedToJob", equipment, source="Console", metadata={"service_job": job_doc.name})
	return _result(job_doc)
