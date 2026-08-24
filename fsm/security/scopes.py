import frappe

SYSTEM_MANAGER = "System Manager"
FSM_MANAGER = "FSM Manager"
FSM_TECHNICIAN = "FSM Technician"
FSM_CUSTOMER = "FSM Customer"


def user_roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def user_permission_values(allow: str, user: str | None = None) -> set[str]:
	user = user or frappe.session.user
	return set(
		frappe.get_all(
			"User Permission",
			filters={"user": user, "allow": allow},
			pluck="for_value",
		)
	)


def allowed_companies(user: str | None = None) -> set[str] | None:
	user = user or frappe.session.user
	if SYSTEM_MANAGER in user_roles(user):
		return None
	return user_permission_values("Company", user)


def allowed_territories(user: str | None = None) -> set[str] | None:
	user = user or frappe.session.user
	if SYSTEM_MANAGER in user_roles(user):
		return None
	values = user_permission_values("Service Territory", user)
	return values or None


def current_technician(user: str | None = None, optional: bool = False) -> str | None:
	user = user or frappe.session.user
	technician = frappe.db.get_value("Technician", {"user": user}) if user and user != "Guest" else None
	if technician or optional:
		return technician
	frappe.throw("No technician profile is linked to your account.", frappe.PermissionError)


def current_customer(user: str | None = None, optional: bool = False) -> str | None:
	user = user or frappe.session.user
	if not user or user == "Guest":
		if optional:
			return None
		raise frappe.AuthenticationError("Please sign in to continue.")

	contact = frappe.db.get_value("Contact", {"user": user})
	customer = None
	if contact:
		customer = frappe.db.get_value(
			"Dynamic Link",
			{"parent": contact, "parenttype": "Contact", "link_doctype": "Customer"},
			"link_name",
		)
	if customer or optional:
		return customer
	frappe.throw("No customer profile is linked to your account.", frappe.PermissionError)


def scoped_job_filters(user: str | None = None) -> dict:
	user = user or frappe.session.user
	roles = user_roles(user)
	if SYSTEM_MANAGER in roles:
		return {}
	if FSM_MANAGER in roles:
		companies = allowed_companies(user) or set()
		filters = {"company": ["in", sorted(companies)]}
		territories = allowed_territories(user)
		if territories is not None:
			filters["territory"] = ["in", sorted(territories)]
		return filters
	if FSM_TECHNICIAN in roles:
		return {"primary_technician": current_technician(user, optional=True) or "__none__"}
	if FSM_CUSTOMER in roles:
		return {"customer": current_customer(user, optional=True) or "__none__"}
	return {"name": "__none__"}


def sql_in_condition(field: str, values: set[str]) -> str:
	if not values:
		return "1=0"
	escaped = ", ".join(frappe.db.escape(value) for value in sorted(values))
	return f"{field} in ({escaped})"
