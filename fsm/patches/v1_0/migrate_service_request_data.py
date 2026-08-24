import frappe


def execute():
	if not frappe.db.table_exists("Service Request"):
		return
	columns = set(frappe.db.get_table_columns("Service Request"))
	assignments = []
	for target, source in (
		("phone", "contact_phone"),
		("description", "notes"),
		("preferred_start", "preferred_date"),
	):
		if target in columns and source in columns:
			assignments.append(f"`{target}` = coalesce(nullif(`{target}`, ''), `{source}`)")
	if "subject" in columns:
		if "customer_name" in columns:
			assignments.append("`subject` = coalesce(nullif(`subject`, ''), concat('Service request from ', coalesce(`customer_name`, `name`)))")
		else:
			assignments.append("`subject` = coalesce(nullif(`subject`, ''), `name`)")
	if assignments:
		frappe.db.sql(f"update `tabService Request` set {', '.join(assignments)}")
	frappe.db.sql("update `tabService Request` set status = 'Triaged' where status = 'Scheduled'")
	frappe.db.sql("update `tabService Request` set source = 'Manual' where source is null or source = ''")
	if "service_job" in columns and frappe.db.has_column("Service Job", "service_request"):
		frappe.db.sql(
			"""update `tabService Job` job join `tabService Request` req on req.service_job = job.name
			set job.service_request = req.name where job.service_request is null or job.service_request = ''"""
		)
