# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import frappe

from fsm.security.policy import require_company_scope, require_role, resolve_manager_company
from fsm.security.scopes import FSM_MANAGER, SYSTEM_MANAGER


@frappe.whitelist()
def list_subcontractors(status: str | None = None):
	require_role(FSM_MANAGER, SYSTEM_MANAGER)
	company = resolve_manager_company()
	filters = {"company": company}
	if status:
		filters["status"] = status
	return frappe.get_list(
		"Subcontractor",
		filters=filters,
		fields=["name", "subcontractor_name", "status", "territory", "hourly_rate", "phone", "email"],
		order_by="subcontractor_name asc",
	)


@frappe.whitelist()
def get_subcontractor_work(subcontractor: str):
	"""A subcontractor's workers, their jobs and a performance summary."""
	company = frappe.db.get_value("Subcontractor", subcontractor, "company")
	require_company_scope(company)
	tech_names = frappe.get_list(
		"Technician",
		filters={"subcontractor": subcontractor, "company": company},
		pluck="name",
	)
	technicians = (
		frappe.get_list(
			"Technician",
			filters={"name": ["in", tech_names]},
			fields=["name", "technician_name", "status", "active"],
		)
		if tech_names
		else []
	)

	jobs = []
	if tech_names:
		jobs = frappe.get_list(
			"Service Job",
			filters={"primary_technician": ["in", tech_names]},
			fields=[
				"name",
				"customer_name",
				"status",
				"scheduled_date",
				"primary_technician",
				"actual_hours",
				"total_cost",
			],
			order_by="scheduled_date desc",
			limit=50,
		)

	completed = [j for j in jobs if j.status == "Completed"]
	summary = {
		"technicians": len(technicians),
		"total_jobs": len(jobs),
		"completed_jobs": len(completed),
		"total_hours": round(sum(j.actual_hours or 0 for j in jobs), 2),
		"total_cost": round(sum(j.total_cost or 0 for j in jobs), 2),
	}
	return {"technicians": technicians, "jobs": jobs, "summary": summary}
