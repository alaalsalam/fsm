from __future__ import annotations

import frappe

from fsm.maintenance.access import require_occurrence_access, require_plan_access
from fsm.security.policy import require_authenticated
from fsm.security.scopes import FSM_CUSTOMER, SYSTEM_MANAGER, allowed_companies, current_customer, user_roles


@frappe.whitelist()
def list_plans(status: str | None = None, customer: str | None = None, company: str | None = None):
	user = require_authenticated()
	roles = user_roles(user)
	filters = {}
	if status:
		filters["status"] = status
	if FSM_CUSTOMER in roles and SYSTEM_MANAGER not in roles:
		filters["customer"] = current_customer(user, optional=True) or "__none__"
	elif customer:
		filters["customer"] = customer
	if FSM_CUSTOMER not in roles and SYSTEM_MANAGER not in roles:
		filters["company"] = ["in", sorted(allowed_companies(user) or set())]
	elif company:
		filters["company"] = company
	return frappe.get_list(
		"Maintenance Plan",
		filters=filters,
		fields=[
			"name",
			"plan_title",
			"customer",
			"company",
			"customer_site",
			"service_contract",
			"status",
			"active",
			"start_date",
			"end_date",
			"revision",
		],
		order_by="modified desc",
		limit=500,
	)


@frappe.whitelist()
def get_plan(maintenance_plan: str):
	return require_plan_access(maintenance_plan, "read").as_dict()


@frappe.whitelist()
def list_occurrences(
	maintenance_plan: str | None = None,
	status: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	limit: int = 500,
):
	require_authenticated()
	filters = {}
	if maintenance_plan:
		require_plan_access(maintenance_plan, "read")
		filters["maintenance_plan"] = maintenance_plan
	if status:
		filters["status"] = status
	if date_from:
		filters["due_date"] = [">=", date_from]
	if date_to:
		filters["due_date"] = ["<=", date_to]
	return frappe.get_list(
		"Maintenance Occurrence",
		filters=filters,
		fields=[
			"name",
			"maintenance_plan",
			"installed_equipment",
			"customer_site",
			"service_type",
			"due_date",
			"release_on",
			"status",
			"released_job",
			"rescheduled_from",
		],
		order_by="due_date asc",
		limit=max(1, min(int(limit), 2000)),
	)


@frappe.whitelist()
def get_occurrence(occurrence: str):
	return require_occurrence_access(occurrence, "read").as_dict()


@frappe.whitelist()
def maintenance_summary(company: str | None = None):
	from frappe.utils import nowdate

	user = require_authenticated()
	roles = user_roles(user)
	filters = {}
	if FSM_CUSTOMER in roles and SYSTEM_MANAGER not in roles:
		filters["customer"] = current_customer(user, optional=True) or "__none__"
	elif SYSTEM_MANAGER not in roles:
		filters["company"] = ["in", sorted(allowed_companies(user) or set())]
	elif company:
		filters["company"] = company
	result = {}
	for status in ("Forecast", "Due", "Overdue", "Released", "Completed", "Skipped"):
		result[status.lower()] = frappe.db.count("Maintenance Occurrence", {**filters, "status": status})
	result["due_today"] = frappe.db.count("Maintenance Occurrence", {**filters, "due_date": nowdate()})
	return result
