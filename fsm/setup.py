# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

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
	],
}


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
	if all(frappe.db.exists("DocType", name) for name in ("Item", "Delivery Note", "Material Request")):
		create_custom_fields(FSM_CUSTOM_FIELDS, ignore_validate=True)


def after_install():
	ensure_roles()
	ensure_custom_fields()


def after_migrate():
	ensure_roles()
	ensure_custom_fields()
