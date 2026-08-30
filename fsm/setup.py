# Copyright (c) 2026, DIGIT and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

FSM_ROLES = (
	("FSM Manager", 1),
	("FSM Technician", 1),
	("FSM Customer", 0),
)

FSM_CUSTOM_FIELDS = {
	"Item": [
		{
			"fieldname": "fsm_after_sales_section",
			"label": "FSM After-Sales",
			"fieldtype": "Section Break",
			"insert_after": "warranty_period",
		},
		{
			"fieldname": "fsm_serviceable",
			"label": "FSM Serviceable",
			"fieldtype": "Check",
			"insert_after": "fsm_after_sales_section",
			"default": "0",
		},
		{
			"fieldname": "fsm_create_installed_equipment",
			"label": "Create Installed Equipment",
			"fieldtype": "Check",
			"insert_after": "fsm_serviceable",
			"depends_on": "eval:doc.fsm_serviceable",
			"default": "0",
		},
		{
			"fieldname": "fsm_tracking_mode",
			"label": "FSM Tracking Mode",
			"fieldtype": "Select",
			"options": "Serial\nUnit\nQuantity\nNone",
			"insert_after": "fsm_create_installed_equipment",
			"depends_on": "eval:doc.fsm_serviceable",
			"default": "None",
		},
		{
			"fieldname": "fsm_activation_on_delivery",
			"label": "Activate on Delivery",
			"fieldtype": "Check",
			"insert_after": "fsm_tracking_mode",
			"depends_on": "eval:doc.fsm_create_installed_equipment",
			"default": "0",
		},
		{
			"fieldname": "fsm_default_warranty_days",
			"label": "Default Warranty Days",
			"fieldtype": "Int",
			"insert_after": "fsm_activation_on_delivery",
			"depends_on": "eval:doc.fsm_serviceable",
			"default": "0",
		},
	],
	"Material Request": [
		{
			"fieldname": "fsm_service_job",
			"label": "Service Job",
			"fieldtype": "Link",
			"options": "Service Job",
			"insert_after": "company",
			"read_only": 1,
		},
		{
			"fieldname": "fsm_service_visit",
			"label": "Service Visit",
			"fieldtype": "Link",
			"options": "Service Visit",
			"insert_after": "fsm_service_job",
			"read_only": 1,
		},
	],
	"Material Request Item": [
		{
			"fieldname": "fsm_installed_equipment",
			"label": "Installed Equipment",
			"fieldtype": "Link",
			"options": "Installed Equipment",
			"insert_after": "item_code",
			"read_only": 1,
		}
	],
	"Pick List": [
		{
			"fieldname": "fsm_service_job",
			"label": "Service Job",
			"fieldtype": "Link",
			"options": "Service Job",
			"insert_after": "company",
			"read_only": 1,
		},
		{
			"fieldname": "fsm_service_visit",
			"label": "Service Visit",
			"fieldtype": "Link",
			"options": "Service Visit",
			"insert_after": "fsm_service_job",
			"read_only": 1,
		},
	],
	"Pick List Item": [
		{
			"fieldname": "fsm_installed_equipment",
			"label": "Installed Equipment",
			"fieldtype": "Link",
			"options": "Installed Equipment",
			"insert_after": "item_code",
			"read_only": 1,
		}
	],
	"Stock Entry": [
		{
			"fieldname": "fsm_service_job",
			"label": "Service Job",
			"fieldtype": "Link",
			"options": "Service Job",
			"insert_after": "company",
			"read_only": 1,
		},
		{
			"fieldname": "fsm_service_visit",
			"label": "Service Visit",
			"fieldtype": "Link",
			"options": "Service Visit",
			"insert_after": "fsm_service_job",
			"read_only": 1,
		},
		{
			"fieldname": "fsm_material_action",
			"label": "FSM Material Action",
			"fieldtype": "Select",
			"options": "\nTransfer\nIssue\nConsume\nReturn",
			"insert_after": "fsm_service_visit",
			"read_only": 1,
		},
	],
	"Stock Entry Detail": [
		{
			"fieldname": "fsm_installed_equipment",
			"label": "Installed Equipment",
			"fieldtype": "Link",
			"options": "Installed Equipment",
			"insert_after": "item_code",
			"read_only": 1,
		}
	],
	"Delivery Note": [
		{
			"fieldname": "fsm_service_job",
			"label": "Service Job",
			"fieldtype": "Link",
			"options": "Service Job",
			"insert_after": "customer",
		},
		{
			"fieldname": "fsm_provisioning_status",
			"label": "FSM Provisioning Status",
			"fieldtype": "Select",
			"options": "\nCompleted\nCancelled\nReturn Reconciled",
			"insert_after": "fsm_service_job",
			"read_only": 1,
		},
		{
			"fieldname": "fsm_installed_equipment_count",
			"label": "Installed Equipment Count",
			"fieldtype": "Int",
			"insert_after": "fsm_provisioning_status",
			"read_only": 1,
		},
		{
			"fieldname": "fsm_service_contract",
			"label": "Service Contract",
			"fieldtype": "Link",
			"options": "Service Contract",
			"insert_after": "fsm_installed_equipment_count",
			"read_only": 1,
		},
	],
	"Quotation": [
		{
			"fieldname": "fsm_service_job",
			"label": "Service Job",
			"fieldtype": "Link",
			"options": "Service Job",
			"insert_after": "company",
			"read_only": 1,
		}
	],
	"Sales Invoice": [
		{
			"fieldname": "fsm_service_job",
			"label": "Service Job",
			"fieldtype": "Link",
			"options": "Service Job",
			"insert_after": "company",
			"read_only": 1,
		},
		{
			"fieldname": "fsm_service_contract",
			"label": "Service Contract",
			"fieldtype": "Link",
			"options": "Service Contract",
			"insert_after": "fsm_service_job",
			"read_only": 1,
		},
	],
}


def ensure_visual_identity():
	"""Keep existing Frappe v16 navigation records aligned with DIGIT branding.

	Workspace records can retain user-customized database values when their standard
	JSON changes. This idempotent system hook updates identity metadata only; names,
	routes, roles, permissions, and workspace links remain untouched.
	"""
	identity_values = {
		"Desktop Icon": {
			"label": "DIGIT Operations & Maintenance",
			"icon": "wrench",
			"logo_url": "/assets/fsm/images/fsm-logo.svg",
		},
		"Workspace Sidebar": {
			"title": "DIGIT Operations & Maintenance",
			"header_icon": "wrench",
		},
		"Workspace": {
			"icon": "wrench",
			"indicator_color": "green",
			"is_hidden": 0,
		},
	}

	for doctype, values in identity_values.items():
		# A standard Desktop Icon can coexist with the branded icon created by the
		# workspace fixture.  Update the branded record when it is present rather
		# than attempting to give both records the same unique label.
		name = "DIGIT Operations & Maintenance" if doctype == "Desktop Icon" and frappe.db.exists(
			doctype, "DIGIT Operations & Maintenance"
		) else "Field Service"
		if frappe.db.exists(doctype, name):
			frappe.db.set_value(doctype, name, values, update_modified=False)


def ensure_field_service_sidebar():
	"""Synchronize the standard Field Service navigation without duplicating it.

	Frappe preserves existing child rows of standard Workspace Sidebars during a
	regular fixture sync.  The navigation is product-owned, so its canonical
	Dashboard → Operations → screens → reports structure is applied explicitly
	during migration while keeping the sidebar's stable name and permissions.
	"""
	path = frappe.get_app_path("fsm", "workspace_sidebar", "field_service.json")
	with open(path, encoding="utf-8") as handle:
		definition = json.load(handle)

	if frappe.db.exists("Workspace Sidebar", definition["name"]):
		sidebar = frappe.get_doc("Workspace Sidebar", definition["name"])
		sidebar.update(
			{
				"title": definition["title"],
				"header_icon": definition["header_icon"],
				"module": definition["module"],
				"app": definition["app"],
			}
		)
		sidebar.set("items", definition["items"])
		sidebar.save()
	else:
		frappe.get_doc(definition).insert()


def ensure_roles():
	for role_name, desk_access in FSM_ROLES:
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role_name,
					"desk_access": desk_access,
				}
			).insert(ignore_permissions=True)


def ensure_custom_fields():
	if all(
		frappe.db.exists("DocType", name)
		for name in (
			"Item",
			"Delivery Note",
			"Material Request",
			"Material Request Item",
			"Pick List",
			"Pick List Item",
			"Stock Entry",
			"Stock Entry Detail",
		)
	):
		create_custom_fields(FSM_CUSTOM_FIELDS, ignore_validate=True)


def after_install():
	ensure_roles()
	ensure_custom_fields()
	ensure_visual_identity()
	ensure_field_service_sidebar()


def after_migrate():
	ensure_roles()
	ensure_custom_fields()
	ensure_visual_identity()
	ensure_field_service_sidebar()
