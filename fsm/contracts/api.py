from __future__ import annotations

import frappe

from fsm.contracts.access import require_contract_access
from fsm.contracts.coverage_engine import evaluate_coverage
from fsm.security.policy import require_authenticated, require_manager_scope, require_role
from fsm.security.scopes import (
	FSM_CUSTOMER,
	FSM_MANAGER,
	SYSTEM_MANAGER,
	allowed_companies,
	current_customer,
	user_roles,
)


@frappe.whitelist()
def list_contracts(status: str | None = None, customer: str | None = None, company: str | None = None):
	user = require_authenticated()
	roles = user_roles(user)
	if not ({FSM_CUSTOMER, FSM_MANAGER, SYSTEM_MANAGER} & roles):
		frappe.throw("You are not permitted to list Service Contracts.", frappe.PermissionError)
	filters = {}
	if status:
		filters["status"] = status
	is_customer_only = FSM_CUSTOMER in roles and not ({FSM_MANAGER, SYSTEM_MANAGER} & roles)
	if is_customer_only:
		filters["customer"] = current_customer(user, optional=True) or "__none__"
	elif customer:
		filters["customer"] = customer
	if not is_customer_only and SYSTEM_MANAGER not in roles:
		filters["company"] = ["in", sorted(allowed_companies(user) or set())]
	elif company:
		filters["company"] = company
	return frappe.get_list(
		"Service Contract",
		filters=filters,
		fields=[
			"name",
			"contract_no",
			"customer",
			"company",
			"status",
			"start_date",
			"end_date",
			"expiring_soon",
			"renewal_recommended",
			"renewal_quotation",
		],
		order_by="end_date asc",
		limit=500,
	)


@frappe.whitelist()
def get_contract(service_contract: str):
	return require_contract_access(service_contract, "read").as_dict()


@frappe.whitelist()
def get_job_coverage(
	service_job: str,
	installed_equipment: str | None = None,
	service_type: str | None = None,
	on_date: str | None = None,
):
	from fsm.security.policy import require_job_access

	job = require_job_access(service_job, "read")
	return evaluate_coverage(job, installed_equipment, service_type, on_date)


@frappe.whitelist()
def list_expiring_contracts(days: int = 30, company: str | None = None):
	from frappe.utils import add_days, cint, nowdate

	require_role(FSM_MANAGER, SYSTEM_MANAGER)
	if company:
		require_manager_scope(company)
	filters = {
		"status": "Active",
		"end_date": ["between", [nowdate(), add_days(nowdate(), max(1, min(cint(days), 365)))]],
	}
	if company:
		filters["company"] = company
	elif SYSTEM_MANAGER not in user_roles():
		filters["company"] = ["in", sorted(allowed_companies() or set())]
	return frappe.get_list(
		"Service Contract",
		filters=filters,
		fields=["name", "customer", "company", "end_date", "renewal_quotation"],
		order_by="end_date asc",
		limit=500,
	)
