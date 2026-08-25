from __future__ import annotations

import frappe
from frappe import _

from fsm.security.policy import require_company_scope, require_customer_ownership, require_job_access
from fsm.security.scopes import FSM_CUSTOMER, FSM_MANAGER, FSM_TECHNICIAN, SYSTEM_MANAGER, user_roles


def require_template_access(template, permission_type="read", user=None):
	doc = template if getattr(template, "doctype", None) else frappe.get_doc("Inspection Template", template)
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return doc
	if FSM_MANAGER in roles:
		require_company_scope(doc.company, user)
		return doc
	if permission_type == "read" and FSM_TECHNICIAN in roles and doc.status == "Active":
		return doc
	frappe.throw(_("This Inspection Template is outside your permitted scope."), frappe.PermissionError)


def require_inspection_access(inspection, permission_type="read", user=None):
	doc = (
		inspection
		if getattr(inspection, "doctype", None)
		else frappe.get_doc("Equipment Inspection", inspection)
	)
	roles = user_roles(user)
	if permission_type == "read" and FSM_CUSTOMER in roles:
		require_customer_ownership(doc.customer, user)
		return doc
	require_job_access(doc.service_job, permission_type, user=user)
	return doc
