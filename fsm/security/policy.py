from collections.abc import Mapping

import frappe
from frappe import _

from fsm.security.scopes import (
	FSM_CUSTOMER,
	FSM_MANAGER,
	FSM_TECHNICIAN,
	SYSTEM_MANAGER,
	allowed_companies,
	allowed_territories,
	current_customer,
	current_technician,
	user_roles,
)


def require_authenticated(user: str | None = None) -> str:
	user = user or frappe.session.user
	if not user or user == "Guest":
		raise frappe.AuthenticationError(_("Please sign in to continue."))
	return user


def require_role(*required_roles: str, user: str | None = None) -> str:
	user = require_authenticated(user)
	if not set(required_roles) & user_roles(user):
		frappe.throw(_("You are not permitted to perform this action."), frappe.PermissionError)
	return user


def require_company_scope(company: str | None, user: str | None = None) -> str:
	user = require_authenticated(user)
	if SYSTEM_MANAGER in user_roles(user):
		return company or ""
	if not company or company not in (allowed_companies(user) or set()):
		frappe.throw(_("This company is outside your permitted scope."), frappe.PermissionError)
	return company


def require_customer_ownership(customer: str | None, user: str | None = None) -> str:
	user = require_role(FSM_CUSTOMER, user=user)
	owned_customer = current_customer(user, optional=True)
	if not customer or customer != owned_customer:
		frappe.throw(_("This record is not on your account."), frappe.PermissionError)
	return customer


def require_technician_assignment(job, user: str | None = None) -> str:
	user = require_role(FSM_TECHNICIAN, user=user)
	technician = current_technician(user)
	job_doc = _job_doc(job)
	if job_doc.primary_technician != technician:
		frappe.throw(_("This job is not assigned to you."), frappe.PermissionError)
	return technician


def require_manager_scope(company: str | None, territory: str | None = None, user: str | None = None) -> str:
	user = require_role(FSM_MANAGER, SYSTEM_MANAGER, user=user)
	require_company_scope(company, user)
	territories = allowed_territories(user)
	if territories is not None and territory and territory not in territories:
		frappe.throw(_("This territory is outside your permitted scope."), frappe.PermissionError)
	return user


def resolve_manager_company(company: str | None = None, user: str | None = None) -> str:
	user = require_role(FSM_MANAGER, SYSTEM_MANAGER, user=user)
	if company:
		require_company_scope(company, user)
		return company
	if SYSTEM_MANAGER in user_roles(user):
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		if company:
			return company
	else:
		companies = allowed_companies(user) or set()
		# Console endpoints do not carry a company parameter on every request.
		# When a manager has more than one authorised company, resolve the
		# standard user default set by the ERP/DIGIT company switcher — but only
		# after proving that it is inside the manager's explicit scope. This keeps
		# the console coherent with the selected company without widening access.
		active_company = frappe.defaults.get_user_default("Company")
		if active_company in companies:
			return active_company
		if len(companies) == 1:
			return next(iter(companies))
	frappe.throw(_("Select a company within your permitted scope."), frappe.PermissionError)


def require_job_access(
	job, permission_type: str = "read", manager_only: bool = False, user: str | None = None
):
	user = require_authenticated(user)
	job_doc = _job_doc(job)
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return job_doc
	if FSM_MANAGER in roles:
		require_manager_scope(job_doc.company, job_doc.territory, user)
		return job_doc
	if manager_only:
		frappe.throw(_("Only an FSM Manager can perform this action."), frappe.PermissionError)
	if FSM_TECHNICIAN in roles:
		require_technician_assignment(job_doc, user)
		return job_doc
	if permission_type == "read" and FSM_CUSTOMER in roles:
		require_customer_ownership(job_doc.customer, user)
		return job_doc
	frappe.throw(_("You are not permitted to access this job."), frappe.PermissionError)


def require_customer_access(customer: str, user: str | None = None) -> str:
	user = require_authenticated(user)
	roles = user_roles(user)
	if FSM_CUSTOMER in roles and not ({FSM_MANAGER, SYSTEM_MANAGER} & roles):
		return require_customer_ownership(customer, user)
	if {FSM_MANAGER, FSM_TECHNICIAN, SYSTEM_MANAGER} & roles:
		visible_job = frappe.get_list(
			"Service Job",
			filters={"customer": customer},
			pluck="name",
			limit=1,
		)
		if visible_job:
			return customer
	frappe.throw(_("This customer is outside your permitted scope."), frappe.PermissionError)


def require_doc_read(doctype: str, name: str, user: str | None = None):
	user = require_authenticated(user)
	doc = frappe.get_doc(doctype, name)
	if doctype == "Service Job":
		return require_job_access(doc, "read", user=user)
	if doctype == "Service Visit":
		require_job_access(doc.service_job, "read", user=user)
		return doc
	frappe.has_permission(doctype, "read", doc=doc, user=user, throw=True)
	return doc


def require_doc_write(doctype: str, name: str, user: str | None = None):
	user = require_authenticated(user)
	doc = frappe.get_doc(doctype, name)
	if doctype == "Service Job":
		return require_job_access(doc, "write", user=user)
	if doctype == "Service Visit":
		require_job_access(doc.service_job, "write", user=user)
		return doc
	frappe.has_permission(doctype, "write", doc=doc, user=user, throw=True)
	return doc


def validate_allowed_fields(values: Mapping, allowed_fields: set[str]) -> None:
	unexpected = set(values) - allowed_fields
	if unexpected:
		frappe.throw(
			_("Unsupported fields: {0}").format(", ".join(sorted(unexpected))),
			frappe.ValidationError,
		)


def bounded_int(value, minimum: int, maximum: int) -> int:
	return max(minimum, min(int(value), maximum))


def _job_doc(job):
	if getattr(job, "doctype", None) == "Service Job":
		return job
	return frappe.get_doc("Service Job", job)
