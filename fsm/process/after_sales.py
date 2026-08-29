from __future__ import annotations

import frappe
from frappe import _

from fsm.security.policy import require_manager_scope


@frappe.whitelist()
def get_after_sales_setup(delivery_note: str):
	"""Read-only setup projection rooted in ERPNext Delivery Note evidence."""
	delivery = frappe.get_doc("Delivery Note", delivery_note)
	frappe.has_permission("Delivery Note", "read", doc=delivery, throw=True)
	require_manager_scope(delivery.company)
	if delivery.docstatus != 1:
		frappe.throw(_("After-sales setup requires a submitted Delivery Note."), frappe.ValidationError)

	equipment = frappe.get_list(
		"Installed Equipment",
		filters={"delivery_note": delivery.name},
		fields=[
			"name",
			"equipment_id",
			"equipment_name",
			"item_code",
			"serial_no",
			"status",
			"customer_site",
			"equipment_location",
			"warranty_status",
			"installation_date",
		],
		order_by="creation asc",
		limit=10000,
	)
	sites = frappe.get_list(
		"Customer Site",
		filters={"company": delivery.company, "customer": delivery.customer},
		fields=["name", "site_name", "status", "address", "territory"],
		order_by="site_name asc",
		limit=500,
	)
	contracts = frappe.get_list(
		"Service Contract",
		filters={"company": delivery.company, "customer": delivery.customer, "status": ["!=", "Cancelled"]},
		fields=["name", "contract_no", "status", "start_date", "end_date", "project"],
		order_by="start_date desc",
		limit=100,
	)
	plans = frappe.get_list(
		"Maintenance Plan",
		filters={"company": delivery.company, "customer": delivery.customer, "status": ["!=", "Cancelled"]},
		fields=["name", "plan_title", "status", "customer_site", "service_contract", "project"],
		order_by="modified desc",
		limit=200,
	)
	plan_names = [row.name for row in plans]
	occurrences = (
		frappe.get_list(
			"Maintenance Occurrence",
			filters={"maintenance_plan": ["in", plan_names]},
			fields=[
				"name",
				"maintenance_plan",
				"installed_equipment",
				"customer_site",
				"service_type",
				"due_date",
				"status",
				"released_job",
			],
			order_by="due_date asc",
			limit=1000,
		)
		if plan_names
		else []
	)
	occurrence_summary = {
		"total": len(occurrences),
		"forecast": sum(1 for row in occurrences if row.status == "Forecast"),
		"due": sum(1 for row in occurrences if row.status == "Due"),
		"overdue": sum(1 for row in occurrences if row.status == "Overdue"),
		"released": sum(1 for row in occurrences if row.released_job),
		"completed": sum(1 for row in occurrences if row.status == "Completed"),
		"next_due_date": next(
			(
				row.due_date
				for row in occurrences
				if row.status in {"Forecast", "Due", "Overdue", "Released"}
			),
			None,
		),
	}

	pending_installation = sum(1 for row in equipment if row.status == "Pending Installation")
	missing_site = sum(1 for row in equipment if not row.customer_site)
	missing_location = sum(1 for row in equipment if row.customer_site and not row.equipment_location)
	return {
		"delivery_note": {
			"name": delivery.name,
			"company": delivery.company,
			"customer": delivery.customer,
			"posting_date": delivery.posting_date,
			"project": delivery.get("project"),
			"provisioning_status": delivery.get("fsm_provisioning_status"),
		},
		"equipment": equipment,
		"sites": sites,
		"contracts": contracts,
		"maintenance_plans": plans,
		"upcoming_occurrences": occurrences[:20],
		"occurrence_summary": occurrence_summary,
		"readiness": {
			"equipment_provisioned": bool(equipment),
			"pending_installation": pending_installation,
			"missing_site": missing_site,
			"missing_location": missing_location,
			"contract_configured": bool(contracts),
			"maintenance_configured": bool(plans),
			"schedule_generated": bool(occurrences),
		},
		"next_action": (
			{"code": "PROVISION_EQUIPMENT", "action": _("Retry provisioning")}
			if not equipment
			else {"code": "ASSIGN_SITE", "action": _("Assign installation sites")}
			if missing_site
			else {"code": "CONFIRM_INSTALLATION", "action": _("Confirm pending installations")}
			if pending_installation
			else {"code": "CONFIGURE_CONTRACT", "action": _("Create or link a service contract")}
			if not contracts
			else {"code": "CONFIGURE_PM", "action": _("Preview preventive maintenance plans")}
			if not plans
			else {"code": "GENERATE_SCHEDULE", "action": _("Activate plans and generate the schedule")}
			if not occurrences
			else {"code": "READY", "action": _("After-sales setup is operational")}
		),
	}
