__version__ = "0.0.1"


def check_app_permission():
	"""Gate the FSM tile on the v16 apps screen: desk users only."""
	import frappe

	if frappe.session.user == "Administrator":
		return True
	user_type = frappe.db.get_value("User", frappe.session.user, "user_type")
	return user_type == "System User"
