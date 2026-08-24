from __future__ import annotations

import frappe
from frappe import _

from fsm.security.policy import require_authenticated, require_customer_ownership, require_manager_scope
from fsm.security.scopes import (
	FSM_CUSTOMER,
	FSM_MANAGER,
	FSM_TECHNICIAN,
	SYSTEM_MANAGER,
	current_technician,
	user_roles,
)


def require_site_access(site, permission_type: str = "read", *, manager_only=False, user=None):
	user = require_authenticated(user)
	doc = site if getattr(site, "doctype", None) else frappe.get_doc("Customer Site", site)
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return doc
	if FSM_MANAGER in roles:
		require_manager_scope(doc.company, doc.territory, user)
		return doc
	if manager_only:
		frappe.throw(_("Only an FSM Manager can perform this action."), frappe.PermissionError)
	if permission_type == "read" and FSM_CUSTOMER in roles:
		require_customer_ownership(doc.customer, user)
		return doc
	if permission_type == "read" and FSM_TECHNICIAN in roles and _technician_can_access_site(doc.name, user):
		return doc
	frappe.throw(_("You are not permitted to access this Customer Site."), frappe.PermissionError)


def require_equipment_access(equipment, permission_type: str = "read", *, manager_only=False, user=None):
	user = require_authenticated(user)
	doc = (
		equipment if getattr(equipment, "doctype", None) else frappe.get_doc("Installed Equipment", equipment)
	)
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return doc
	if FSM_MANAGER in roles:
		require_manager_scope(doc.company, None, user)
		return doc
	if manager_only:
		frappe.throw(_("Only an FSM Manager can perform this action."), frappe.PermissionError)
	if permission_type == "read" and FSM_CUSTOMER in roles:
		require_customer_ownership(doc.customer, user)
		return doc
	if (
		permission_type == "read"
		and FSM_TECHNICIAN in roles
		and _technician_can_access_equipment(doc.name, user)
	):
		return doc
	frappe.throw(_("You are not permitted to access this Installed Equipment."), frappe.PermissionError)


def require_location_access(location, permission_type="read", *, manager_only=False, user=None):
	doc = location if getattr(location, "doctype", None) else frappe.get_doc("Equipment Location", location)
	require_site_access(doc.customer_site, permission_type, manager_only=manager_only, user=user)
	return doc


def _technician_can_access_equipment(equipment: str, user: str) -> bool:
	technician = current_technician(user, True)
	if not technician:
		return False
	return bool(
		frappe.db.sql(
			"""select 1 from `tabService Job Equipment` eq
			join `tabService Job` job on job.name = eq.parent
			where eq.parenttype = 'Service Job' and eq.installed_equipment = %s
			and job.primary_technician = %s limit 1""",
			(equipment, technician),
		)
	)


def _technician_can_access_site(site: str, user: str) -> bool:
	technician = current_technician(user, True)
	if not technician:
		return False
	return bool(
		frappe.db.sql(
			"""select 1 from `tabService Job Equipment` eq
			join `tabService Job` job on job.name = eq.parent
			where eq.parenttype = 'Service Job' and eq.customer_site = %s
			and job.primary_technician = %s limit 1""",
			(site, technician),
		)
	)
