import frappe


def execute():
	if not frappe.db.table_exists("Service Return"):
		return
	for old, new in {
		"Requested": "Pickup Requested",
		"Approved": "Picked Up",
		"Received": "Workshop Received",
	}.items():
		frappe.db.set_value("Service Return", {"status": old}, "status", new, update_modified=False)
