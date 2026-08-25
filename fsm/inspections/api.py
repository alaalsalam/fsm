from __future__ import annotations

import frappe

from fsm.inspections.access import require_inspection_access, require_template_access
from fsm.security.policy import require_authenticated


@frappe.whitelist()
def list_templates(company: str | None = None, status: str | None = "Active", item_group: str | None = None):
	require_authenticated()
	filters = {}
	if company:
		filters["company"] = company
	if status:
		filters["status"] = status
	if item_group:
		filters["item_group"] = item_group
	return frappe.get_list(
		"Inspection Template",
		filters=filters,
		fields=["name", "template_name", "company", "status", "active", "revision", "item_group", "modified"],
		order_by="modified desc",
		limit=500,
	)


@frappe.whitelist()
def get_template(inspection_template: str):
	return require_template_access(inspection_template, "read").as_dict()


@frappe.whitelist()
def list_inspections(
	service_job: str | None = None,
	installed_equipment: str | None = None,
	status: str | None = None,
	overall_result: str | None = None,
	limit: int = 500,
):
	require_authenticated()
	filters = {}
	if service_job:
		from fsm.security.policy import require_job_access

		require_job_access(service_job, "read")
		filters["service_job"] = service_job
	if installed_equipment:
		filters["installed_equipment"] = installed_equipment
	if status:
		filters["status"] = status
	if overall_result:
		filters["overall_result"] = overall_result
	return frappe.get_list(
		"Equipment Inspection",
		filters=filters,
		fields=[
			"name",
			"installed_equipment",
			"service_job",
			"service_visit",
			"inspection_template",
			"technician",
			"customer",
			"customer_site",
			"status",
			"started_on",
			"completed_on",
			"overall_result",
			"corrective_action_hint",
		],
		order_by="started_on desc",
		limit=max(1, min(int(limit), 2000)),
	)


@frappe.whitelist()
def get_inspection(inspection: str):
	return require_inspection_access(inspection, "read").as_dict()
