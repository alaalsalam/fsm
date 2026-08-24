import frappe


def execute():
	"""Rename the intake DocType in place so names, audit history and links survive upgrade."""
	if frappe.db.exists("DocType", "Service Appointment") and not frappe.db.exists(
		"DocType", "Service Request"
	):
		frappe.rename_doc("DocType", "Service Appointment", "Service Request", force=True)
