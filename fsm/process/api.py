from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, nowdate

from fsm.process.completion import completion_blockers
from fsm.process.next_action import next_action_for
from fsm.security.policy import bounded_int, require_authenticated, require_job_access, require_manager_scope


def _manager_company(company=None):
	require_authenticated()
	if company:
		require_manager_scope(company)
		return company
	from fsm.security.policy import resolve_manager_company

	return resolve_manager_company()


@frappe.whitelist()
def get_next_action(reference_doctype: str, reference_name: str):
	if reference_doctype == "Service Job":
		doc = require_job_access(reference_name, "read")
	elif reference_doctype == "Service Visit":
		doc = frappe.get_doc(reference_doctype, reference_name)
		require_job_access(doc.service_job, "read")
	elif reference_doctype in {
		"Service Request",
		"Maintenance Occurrence",
		"Service Contract",
		"Service Return",
	}:
		doc = frappe.get_doc(reference_doctype, reference_name)
		require_manager_scope(doc.company)
	else:
		frappe.throw(_("Unsupported operational reference."))
	return next_action_for(doc)


@frappe.whitelist()
def get_job_hub(service_job: str):
	job = require_job_access(service_job, "read")
	return {
		"job": job.as_dict(),
		"next_action": next_action_for(job),
		"completion_blockers": completion_blockers(job),
		"visits": frappe.get_list(
			"Service Visit",
			filters={"service_job": job.name},
			fields=[
				"name",
				"status",
				"service_team",
				"primary_technician",
				"scheduled_start",
				"scheduled_end",
				"actual_check_in",
				"actual_check_out",
				"actual_completion",
			],
			order_by="scheduled_start asc",
		),
		"inspections": frappe.get_list(
			"Equipment Inspection",
			filters={"service_job": job.name},
			fields=[
				"name",
				"installed_equipment",
				"service_visit",
				"status",
				"overall_result",
				"completed_on",
			],
			order_by="creation asc",
		),
		"failures": frappe.get_list(
			"Failure Analysis",
			filters={"service_job": job.name},
			fields=["name", "installed_equipment", "severity", "status", "root_cause"],
			order_by="creation asc",
		),
		"workshop": frappe.get_list(
			"Service Return",
			filters={"service_job": job.name},
			fields=["name", "installed_equipment", "status", "quotation", "sales_invoice"],
			order_by="creation asc",
		),
		"reports": frappe.get_list(
			"Service Report",
			filters={"service_job": job.name},
			fields=["name", "report_type", "revision", "status", "submitted_on"],
			order_by="revision desc",
		),
		"certificates": frappe.get_list(
			"Service Certificate",
			filters={"service_job": job.name},
			fields=["name", "certificate_type", "installed_equipment", "status", "issued_on"],
			order_by="issued_on desc",
		),
	}


@frappe.whitelist()
def list_visits(
	company: str | None = None,
	status: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	job: str | None = None,
	limit=100,
):
	company = _manager_company(company)
	conditions = ["job.company = %(company)s"]
	values = {"company": company, "limit": bounded_int(limit, 1, 500)}
	if status:
		conditions.append("visit.status = %(status)s")
		values["status"] = status
	if job:
		conditions.append("visit.service_job = %(job)s")
		values["job"] = job
	if date_from:
		conditions.append("visit.scheduled_start >= %(date_from)s")
		values["date_from"] = date_from
	if date_to:
		conditions.append("visit.scheduled_start < date_add(%(date_to)s, interval 1 day)")
		values["date_to"] = date_to
	return frappe.db.sql(
		f"""select visit.name, visit.scheduled_start, visit.scheduled_end, visit.status,
			visit.service_job, visit.service_team, visit.primary_technician,
			visit.actual_check_in, visit.actual_check_out, visit.actual_completion,
			job.customer, job.customer_name, job.service_type, job.project,
			job.assigned_service_team, job.team_leader,
			(select count(*) from `tabService Job Equipment` eq where eq.parent = job.name) equipment_count
		from `tabService Visit` visit
		inner join `tabService Job` job on job.name = visit.service_job
		where {" and ".join(conditions)}
		order by coalesce(visit.scheduled_start, visit.creation) asc
		limit %(limit)s""",
		values,
		as_dict=True,
	)


@frappe.whitelist()
def get_operations_home(company: str | None = None):
	company = _manager_company(company)
	today = nowdate()
	visits_today = frappe.db.sql(
		"""select count(*) from `tabService Visit` visit
		inner join `tabService Job` job on job.name = visit.service_job
		where job.company = %(company)s and visit.status != 'Cancelled'
		and visit.scheduled_start >= %(today)s
		and visit.scheduled_start < date_add(%(today)s, interval 1 day)""",
		{"company": company, "today": today},
	)[0][0]
	return {
		"company": company,
		"visits_today": visits_today,
		"unassigned_jobs": frappe.db.count(
			"Service Job",
			{
				"company": company,
				"status": ["not in", ["Completed", "Cancelled"]],
				"assigned_service_team": ["is", "not set"],
			},
		),
		"in_progress": frappe.db.count("Service Job", {"company": company, "status": "In Progress"}),
		"on_hold": frappe.db.count("Service Job", {"company": company, "status": "On Hold"}),
		"overdue_pm": frappe.db.count("Maintenance Occurrence", {"company": company, "status": "Overdue"}),
		"reports_awaiting_signature": frappe.db.count(
			"Service Report", {"company": company, "status": ["in", ["Generated", "Customer Review"]]}
		),
		"contracts_expiring_30_days": frappe.db.count(
			"Service Contract",
			{"company": company, "status": "Active", "end_date": ["between", [today, add_days(today, 30)]]},
		),
	}


@frappe.whitelist()
def list_exceptions(company: str | None = None, limit=100):
	company = _manager_company(company)
	rows = []
	for job in frappe.get_all(
		"Service Job",
		filters={
			"company": company,
			"status": ["not in", ["Completed", "Cancelled"]],
			"assigned_service_team": ["is", "not set"],
		},
		fields=["name", "customer", "status", "creation"],
		limit=bounded_int(limit, 1, 200),
	):
		rows.append(
			{
				"type": "Unassigned Job",
				"severity": "High",
				"reference_doctype": "Service Job",
				"reference": job.name,
				"customer": job.customer,
				"reason": _("No service team is assigned"),
				"created_on": job.creation,
				"action": "Assign Team",
			}
		)
	for occurrence in frappe.get_all(
		"Maintenance Occurrence",
		filters={"company": company, "status": "Overdue"},
		fields=["name", "customer", "customer_site", "due_date"],
		limit=bounded_int(limit, 1, 200),
	):
		rows.append(
			{
				"type": "Overdue Maintenance",
				"severity": "High",
				"reference_doctype": "Maintenance Occurrence",
				"reference": occurrence.name,
				"customer": occurrence.customer,
				"site": occurrence.customer_site,
				"reason": _("Maintenance is overdue since {0}").format(occurrence.due_date),
				"created_on": occurrence.due_date,
				"action": "Release Job",
			}
		)
	for report in frappe.get_all(
		"Service Report",
		filters={"company": company, "status": ["in", ["Generated", "Customer Review"]]},
		fields=["name", "customer", "customer_site", "service_job", "modified"],
		limit=bounded_int(limit, 1, 200),
	):
		rows.append(
			{
				"type": "Report Awaiting Signature",
				"severity": "Medium",
				"reference_doctype": "Service Report",
				"reference": report.name,
				"customer": report.customer,
				"site": report.customer_site,
				"reason": _("Customer signature or refusal is pending"),
				"created_on": report.modified,
				"action": "Open Report",
				"parent": report.service_job,
			}
		)
	return sorted(rows, key=lambda row: str(row.get("created_on") or ""))[: bounded_int(limit, 1, 500)]


@frappe.whitelist()
def get_customer_360(customer: str, company: str | None = None):
	company = _manager_company(company)
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Customer not found."), frappe.DoesNotExistError)
	return {
		"customer": frappe.db.get_value(
			"Customer",
			customer,
			["name", "customer_name", "customer_group", "territory", "mobile_no", "email_id"],
			as_dict=True,
		),
		"sites": frappe.get_list(
			"Customer Site",
			filters={"customer": customer, "company": company},
			fields=["name", "site_name", "status", "city", "territory"],
			order_by="site_name asc",
			limit=500,
		),
		"equipment": frappe.get_list(
			"Installed Equipment",
			filters={"customer": customer, "company": company},
			fields=[
				"name",
				"equipment_id",
				"equipment_name",
				"status",
				"customer_site",
				"equipment_location",
				"item_code",
				"serial_no",
				"warranty_status",
				"last_service_date",
			],
			order_by="modified desc",
			limit=500,
		),
		"contracts": frappe.get_list(
			"Service Contract",
			filters={"customer": customer, "company": company, "status": ["!=", "Cancelled"]},
			fields=["name", "contract_no", "status", "project", "start_date", "end_date"],
			order_by="end_date desc",
			limit=200,
		),
		"maintenance_plans": frappe.get_list(
			"Maintenance Plan",
			filters={"customer": customer, "company": company, "status": ["!=", "Cancelled"]},
			fields=["name", "plan_title", "status", "project", "customer_site", "service_contract"],
			order_by="modified desc",
			limit=200,
		),
		"jobs": frappe.get_list(
			"Service Job",
			filters={"customer": customer, "company": company},
			fields=["name", "status", "phase", "project", "service_type", "scheduled_date", "completed_on"],
			order_by="creation desc",
			limit=200,
		),
		"requests": frappe.get_list(
			"Service Request",
			filters={"customer": customer, "company": company},
			fields=["name", "subject", "status", "project", "creation"],
			order_by="creation desc",
			limit=200,
		),
		"commercial": {
			"quotations": frappe.get_list(
				"Quotation",
				filters={"party_name": customer, "company": company, "docstatus": ["<", 2]},
				fields=["name", "status", "grand_total", "transaction_date"],
				order_by="transaction_date desc",
				limit=100,
			),
			"invoices": frappe.get_list(
				"Sales Invoice",
				filters={"customer": customer, "company": company, "docstatus": ["<", 2]},
				fields=["name", "status", "grand_total", "outstanding_amount", "posting_date"],
				order_by="posting_date desc",
				limit=100,
			),
		},
	}
