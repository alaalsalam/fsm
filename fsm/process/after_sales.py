from __future__ import annotations

import frappe
from frappe import _

from fsm.security.policy import require_authenticated, require_manager_scope, require_role
from fsm.security.scopes import FSM_MANAGER, SYSTEM_MANAGER, allowed_companies, user_roles


@frappe.whitelist()
def search_submitted_delivery_notes(query: str = "", limit: int = 20):
	"""Permission-scoped Delivery Note picker for the after-sales journey."""
	user = require_authenticated()
	require_role(FSM_MANAGER, SYSTEM_MANAGER)
	filters: dict = {"docstatus": 1, "is_return": 0}
	if SYSTEM_MANAGER not in user_roles(user):
		filters["company"] = ["in", sorted(allowed_companies(user) or set())]
	or_filters = None
	if query := (query or "").strip():
		or_filters = {"name": ["like", f"%{query}%"], "customer": ["like", f"%{query}%"]}
	rows = frappe.get_list(
		"Delivery Note",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "customer", "company", "posting_date", "fsm_service_contract"],
		order_by="posting_date desc, modified desc",
		limit_page_length=max(1, min(int(limit), 50)),
	)
	return [
		{
			"value": row.name,
			"label": f"{row.name} · {row.customer}",
			"description": f"{row.company} · {row.posting_date}",
		}
		for row in rows
	]


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
	linked_contract = delivery.get("fsm_service_contract")
	contract_filters = (
		{"name": linked_contract, "status": ["!=", "Cancelled"]}
		if linked_contract
		else {"delivery_note": delivery.name, "status": ["!=", "Cancelled"]}
	)
	contracts = frappe.get_list(
		"Service Contract",
		filters=contract_filters,
		fields=[
			"name",
			"contract_no",
			"status",
			"start_date",
			"end_date",
			"project",
			"delivery_note",
			"sales_invoice",
			"maintenance_service_type",
			"maintenance_interval_count",
			"maintenance_interval_unit",
			"first_maintenance_date",
		],
		order_by="start_date desc",
		limit=10,
	)
	contract_names = [row.name for row in contracts]
	plans = (
		frappe.get_list(
			"Maintenance Plan",
			filters={"service_contract": ["in", contract_names], "status": ["!=", "Cancelled"]},
			fields=["name", "plan_title", "status", "customer_site", "service_contract", "project"],
			order_by="modified desc",
			limit=200,
		)
		if contract_names
		else []
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
			(row.due_date for row in occurrences if row.status in {"Forecast", "Due", "Overdue", "Released"}),
			None,
		),
	}

	pending_installation = sum(1 for row in equipment if row.status == "Pending Installation")
	missing_site = sum(1 for row in equipment if not row.customer_site)
	missing_location = sum(1 for row in equipment if row.customer_site and not row.equipment_location)
	active_contract = next((row for row in contracts if row.status == "Active"), None)
	draft_contract = next((row for row in contracts if row.status == "Draft"), None)
	draft_plans = [row for row in plans if row.status in {"Draft", "Paused"}]
	return {
		"delivery_note": {
			"name": delivery.name,
			"company": delivery.company,
			"customer": delivery.customer,
			"posting_date": delivery.posting_date,
			"project": delivery.get("project"),
			"provisioning_status": delivery.get("fsm_provisioning_status"),
			"service_contract": linked_contract,
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
			"contract_active": bool(active_contract),
			"maintenance_configured": bool(plans),
			"plans_awaiting_approval": len(draft_plans),
			"schedule_generated": bool(occurrences),
		},
		"next_action": (
			{"code": "PROVISION_EQUIPMENT", "action": _("Retry provisioning")}
			if not equipment
			else {"code": "ASSIGN_SITE", "action": _("Assign installation sites")}
			if missing_site
			else {"code": "CONFIRM_INSTALLATION", "action": _("Confirm pending installations")}
			if pending_installation
			else {"code": "PREPARE_CONTRACT", "action": _("Prepare the draft service contract")}
			if not contracts
			else {"code": "REVIEW_CONTRACT", "action": _("Review and activate the draft service contract")}
			if draft_contract
			else {"code": "PREPARE_PM", "action": _("Prepare maintenance plans from the active contract")}
			if active_contract and not plans
			else {"code": "APPROVE_PLANS", "action": _("Review and activate maintenance plans")}
			if draft_plans
			else {"code": "GENERATE_SCHEDULE", "action": _("Generate the recurring maintenance schedule")}
			if plans and not occurrences
			else {"code": "READY", "action": _("After-sales setup is operational")}
		),
	}
