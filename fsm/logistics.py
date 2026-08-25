# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import frappe

from fsm.security.policy import require_job_access


@frappe.whitelist()
def request_parts(
	job: str,
	items,
	warehouse: str | None = None,
	material_request_type: str = "Material Transfer",
	schedule_date: str | None = None,
):
	"""Compatibility alias for the canonical ERPNext-backed shortage command."""
	if material_request_type != "Material Transfer":
		frappe.throw("FSM material requirements must use ERPNext Material Transfer requests.")
	from fsm.materials import request_shortage

	return request_shortage(job, items, warehouse=warehouse, schedule_date=schedule_date)


@frappe.whitelist()
def get_job_logistics(job: str):
	"""Parts requests and deliveries linked to a job, for the job timeline."""
	require_job_access(job, "read")
	material_requests = frappe.get_list(
		"Material Request",
		filters={"fsm_service_job": job},
		fields=[
			"name",
			"status",
			"material_request_type",
			"transaction_date",
			"schedule_date",
			"per_ordered",
			"per_received",
		],
		order_by="creation desc",
	)
	delivery_notes = frappe.get_list(
		"Delivery Note",
		filters={"fsm_service_job": job},
		fields=["name", "status", "posting_date", "per_billed"],
		order_by="creation desc",
	)
	return {"material_requests": material_requests, "delivery_notes": delivery_notes}


def _job_warehouse(job: str) -> str | None:
	"""Resolve team → technician van → settings warehouse (compatibility helper)."""
	team = frappe.db.get_value("Service Job", job, "assigned_service_team")
	if team:
		warehouse = frappe.db.get_value("Service Team", team, "default_warehouse")
		if warehouse:
			return warehouse
	technician = frappe.db.get_value("Service Job", job, "primary_technician")
	if technician:
		van = frappe.db.get_value("Technician", technician, "warehouse")
		if van:
			return van
	return frappe.db.get_single_value("Service Settings", "default_warehouse")
