from __future__ import annotations

import frappe
from frappe import _

from fsm.security.policy import require_authenticated, require_company_scope, require_customer_ownership
from fsm.security.scopes import FSM_CUSTOMER, FSM_MANAGER, FSM_TECHNICIAN, SYSTEM_MANAGER, user_roles


def require_plan_access(plan, permission_type="read", manager_only=False, user=None):
	user = require_authenticated(user)
	doc = plan if getattr(plan, "doctype", None) else frappe.get_doc("Maintenance Plan", plan)
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return doc
	if FSM_MANAGER in roles:
		require_company_scope(doc.company, user)
		return doc
	if manager_only:
		frappe.throw(_("Only an FSM Manager can perform this maintenance action."), frappe.PermissionError)
	if permission_type == "read" and FSM_CUSTOMER in roles:
		require_customer_ownership(doc.customer, user)
		return doc
	frappe.throw(_("This Maintenance Plan is outside your permitted scope."), frappe.PermissionError)


def require_occurrence_access(occurrence, permission_type="read", manager_only=False, user=None):
	user = require_authenticated(user)
	doc = (
		occurrence
		if getattr(occurrence, "doctype", None)
		else frappe.get_doc("Maintenance Occurrence", occurrence)
	)
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return doc
	if FSM_MANAGER in roles:
		require_company_scope(doc.company, user)
		return doc
	if manager_only:
		frappe.throw(_("Only an FSM Manager can perform this occurrence action."), frappe.PermissionError)
	if permission_type == "read" and FSM_CUSTOMER in roles:
		require_customer_ownership(doc.customer, user)
		return doc
	if permission_type == "read" and FSM_TECHNICIAN in roles and doc.released_job:
		from fsm.security.policy import require_job_access

		require_job_access(doc.released_job, "read", user=user)
		return doc
	frappe.throw(_("This Maintenance Occurrence is outside your permitted scope."), frappe.PermissionError)
