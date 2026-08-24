import frappe

from fsm.installed_base.access import require_equipment_access, require_location_access, require_site_access
from fsm.security.policy import require_job_access, require_manager_scope
from fsm.security.scopes import (
	FSM_CUSTOMER,
	FSM_MANAGER,
	FSM_TECHNICIAN,
	SYSTEM_MANAGER,
	allowed_companies,
	allowed_territories,
	current_customer,
	current_technician,
	sql_in_condition,
	user_roles,
)


def service_job_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return ""
	if FSM_MANAGER in roles:
		conditions = [sql_in_condition("`tabService Job`.`company`", allowed_companies(user) or set())]
		territories = allowed_territories(user)
		if territories is not None:
			conditions.append(sql_in_condition("`tabService Job`.`territory`", territories))
		return " and ".join(f"({condition})" for condition in conditions)
	if FSM_TECHNICIAN in roles:
		return f"`tabService Job`.`primary_technician` = {frappe.db.escape(current_technician(user, True) or '__none__')}"
	if FSM_CUSTOMER in roles:
		return f"`tabService Job`.`customer` = {frappe.db.escape(current_customer(user, True) or '__none__')}"
	return "1=0"


def service_job_permission(doc, user: str | None = None, permission_type: str | None = None):
	try:
		require_job_access(doc, permission_type or "read", user=user)
	except frappe.AuthenticationError, frappe.PermissionError:
		return False
	return True


def service_request_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return ""
	if FSM_MANAGER in roles:
		conditions = [
			sql_in_condition("`tabService Request`.`company`", allowed_companies(user) or set())
		]
		territories = allowed_territories(user)
		if territories is not None:
			conditions.append(sql_in_condition("`tabService Request`.`territory`", territories))
		return " and ".join(f"({condition})" for condition in conditions)
	if FSM_CUSTOMER in roles:
		return f"`tabService Request`.`customer` = {frappe.db.escape(current_customer(user, True) or '__none__')}"
	return "1=0"


def service_request_permission(doc, user: str | None = None, permission_type: str | None = None):
	user = user or frappe.session.user
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return True
	if FSM_MANAGER in roles:
		try:
			require_manager_scope(doc.company, doc.territory, user)
		except frappe.PermissionError:
			return False
		return True
	if permission_type == "read" and FSM_CUSTOMER in roles:
		return doc.customer == current_customer(user, True)
	return False


def service_visit_query(user: str | None = None) -> str:
	return job_child_query("Service Visit", user=user)


def service_visit_permission(doc, user: str | None = None, permission_type: str | None = None):
	return job_child_permission(doc, user, permission_type)


def event_log_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return ""
	job_scope = service_job_query(user)
	request_scope = service_request_query(user)
	equipment_scope = installed_equipment_query(user)
	return (
		f"((`tabService Event Log`.`service_job` is not null and exists (select 1 from `tabService Job` "
		f"where `tabService Job`.`name` = `tabService Event Log`.`service_job` and ({job_scope or '1=1'}))) "
		f"or (`tabService Event Log`.`service_request` is not null and exists (select 1 from `tabService Request` "
		f"where `tabService Request`.`name` = `tabService Event Log`.`service_request` and ({request_scope or '1=1'}))) "
		f"or (`tabService Event Log`.`installed_equipment` is not null and exists (select 1 from `tabInstalled Equipment` "
		f"where `tabInstalled Equipment`.`name` = `tabService Event Log`.`installed_equipment` and ({equipment_scope or '1=1'}))))"
	)


def event_log_permission(doc, user: str | None = None, permission_type: str | None = None):
	if permission_type not in (None, "read"):
		return False
	if doc.service_job:
		try:
			require_job_access(doc.service_job, "read", user=user)
		except (frappe.AuthenticationError, frappe.PermissionError):
			return False
		return True
	if doc.service_request:
		return service_request_permission(
			frappe.get_doc("Service Request", doc.service_request), user, "read"
		)
	if doc.installed_equipment:
		try:
			require_equipment_access(doc.installed_equipment, "read", user=user)
		except (frappe.AuthenticationError, frappe.PermissionError):
			return False
		return True
	return False


def customer_site_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return ""
	if FSM_MANAGER in roles:
		conditions = [sql_in_condition("`tabCustomer Site`.`company`", allowed_companies(user) or set())]
		territories = allowed_territories(user)
		if territories is not None:
			conditions.append(sql_in_condition("`tabCustomer Site`.`territory`", territories))
		return " and ".join(f"({condition})" for condition in conditions)
	if FSM_CUSTOMER in roles:
		return f"`tabCustomer Site`.`customer` = {frappe.db.escape(current_customer(user, True) or '__none__')}"
	if FSM_TECHNICIAN in roles:
		technician = frappe.db.escape(current_technician(user, True) or "__none__")
		return (
			"exists (select 1 from `tabService Job Equipment` eq join `tabService Job` job on job.name = eq.parent "
			f"where eq.parenttype = 'Service Job' and eq.customer_site = `tabCustomer Site`.`name` and job.primary_technician = {technician})"
		)
	return "1=0"


def customer_site_permission(doc, user: str | None = None, permission_type: str | None = None):
	try:
		require_site_access(doc, permission_type or "read", user=user)
	except (frappe.AuthenticationError, frappe.PermissionError):
		return False
	return True


def installed_equipment_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return ""
	if FSM_MANAGER in roles:
		return sql_in_condition("`tabInstalled Equipment`.`company`", allowed_companies(user) or set())
	if FSM_CUSTOMER in roles:
		return f"`tabInstalled Equipment`.`customer` = {frappe.db.escape(current_customer(user, True) or '__none__')}"
	if FSM_TECHNICIAN in roles:
		technician = frappe.db.escape(current_technician(user, True) or "__none__")
		return (
			"exists (select 1 from `tabService Job Equipment` eq join `tabService Job` job on job.name = eq.parent "
			f"where eq.parenttype = 'Service Job' and eq.installed_equipment = `tabInstalled Equipment`.`name` and job.primary_technician = {technician})"
		)
	return "1=0"


def installed_equipment_permission(doc, user: str | None = None, permission_type: str | None = None):
	try:
		require_equipment_access(doc, permission_type or "read", user=user)
	except (frappe.AuthenticationError, frappe.PermissionError):
		return False
	return True


def equipment_location_query(user: str | None = None) -> str:
	site_scope = customer_site_query(user)
	return (
		"exists (select 1 from `tabCustomer Site` where `tabCustomer Site`.`name` = "
		f"`tabEquipment Location`.`customer_site` and ({site_scope or '1=1'}))"
	)


def equipment_location_permission(doc, user: str | None = None, permission_type: str | None = None):
	try:
		require_location_access(doc, permission_type or "read", user=user)
	except (frappe.AuthenticationError, frappe.PermissionError):
		return False
	return True


def job_child_query(doctype: str, job_field: str = "service_job", user: str | None = None) -> str:
	job_scope = service_job_query(user)
	return (
		f"exists (select 1 from `tabService Job` where `tabService Job`.`name` = "
		f"`tab{doctype}`.`{job_field}` and ({job_scope or '1=1'}))"
	)


def service_return_query(user: str | None = None) -> str:
	return job_child_query("Service Return", user=user)


def message_query(user: str | None = None) -> str:
	return job_child_query("Service Job Message", user=user)


def feedback_query(user: str | None = None) -> str:
	return job_child_query("Service Feedback", user=user)


def time_log_query(user: str | None = None) -> str:
	return job_child_query("Service Time Log", user=user)


def field_note_query(user: str | None = None) -> str:
	return job_child_query("Customer Field Note", user=user)


def location_log_query(user: str | None = None) -> str:
	return job_child_query("Technician Location Log", user=user)


def job_child_permission(doc, user: str | None = None, permission_type: str | None = None):
	if not doc.service_job:
		return False
	try:
		root_permission = "read" if permission_type in (None, "read", "create") else "write"
		job = require_job_access(doc.service_job, root_permission, user=user)
	except frappe.AuthenticationError, frappe.PermissionError:
		return False
	if getattr(doc, "customer", None) and doc.customer != job.customer:
		return False
	roles = user_roles(user)
	if (
		permission_type in ("create", "write")
		and FSM_TECHNICIAN in roles
		and getattr(doc, "technician", None)
		and doc.technician != current_technician(user, True)
	):
		return False
	return True
