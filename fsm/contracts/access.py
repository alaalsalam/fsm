from __future__ import annotations

import frappe
from frappe import _

from fsm.security.policy import require_authenticated, require_company_scope, require_customer_ownership
from fsm.security.scopes import (
	FSM_CUSTOMER,
	FSM_MANAGER,
	FSM_TECHNICIAN,
	SYSTEM_MANAGER,
	current_technician,
	user_roles,
)


def require_contract_access(contract, permission_type: str = "read", manager_only: bool = False, user=None):
	user = require_authenticated(user)
	doc = contract if getattr(contract, "doctype", None) else frappe.get_doc("Service Contract", contract)
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return doc
	if FSM_MANAGER in roles:
		require_company_scope(doc.company, user)
		return doc
	if manager_only:
		frappe.throw(_("Only an FSM Manager can perform this Contract action."), frappe.PermissionError)
	if permission_type == "read" and FSM_CUSTOMER in roles:
		require_customer_ownership(doc.customer, user)
		return doc
	if permission_type == "read" and FSM_TECHNICIAN in roles:
		technician = current_technician(user, optional=True)
		if technician and frappe.db.exists(
			"Service Job", {"service_contract": doc.name, "primary_technician": technician}
		):
			return doc
	frappe.throw(_("This Service Contract is outside your permitted scope."), frappe.PermissionError)
