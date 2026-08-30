from __future__ import annotations

import frappe
from frappe.utils import add_days, nowdate

from fsm.security.policy import require_customer_ownership
from fsm.security.scopes import current_customer


def _customer():
	customer = current_customer()
	require_customer_ownership(customer)
	return customer


@frappe.whitelist()
def get_my_portal_hub():
	"""Customer-only after-sales projection. Never returns internal cost, stock or staff notes."""
	customer = _customer()
	jobs = frappe.get_list(
		"Service Job",
		filters={"customer": customer},
		fields=["name", "status", "phase", "service_type", "scheduled_date", "scheduled_end", "completed_on", "coverage_status", "service_contract", "quotation", "sales_invoice", "primary_technician", "assigned_service_team", "address_display"],
		order_by="creation desc",
		limit=500,
	)
	job_names = [row.name for row in jobs]
	visits = (
		frappe.get_all(
			"Service Visit",
			filters={"service_job": ["in", job_names], "status": ["!=", "Cancelled"]},
			fields=["name", "service_job", "status", "scheduled_start", "scheduled_end", "service_team", "primary_technician", "actual_completion"],
			order_by="scheduled_start asc",
			limit=500,
		)
		if job_names else []
	)
	items = (
		frappe.get_all(
			"Service Job Item",
			filters={"parent": ["in", job_names]},
			fields=["parent", "item_code", "item_name", "material_type", "qty", "uom", "installed_equipment", "amount"],
			order_by="parent asc, idx asc",
			limit=1000,
		)
		if job_names else []
	)
	job_equipment = (
		frappe.get_all(
			"Service Job Equipment",
			filters={"parent": ["in", job_names]},
			fields=["parent", "installed_equipment", "customer_site"],
			order_by="parent asc, idx asc",
			limit=1000,
		)
		if job_names else []
	)
	job_context = {}
	for row in job_equipment:
		context = job_context.setdefault(row.parent, {"sites": [], "equipment": []})
		if row.customer_site and row.customer_site not in context["sites"]:
			context["sites"].append(row.customer_site)
		if row.installed_equipment:
			context["equipment"].append(row.installed_equipment)
	for job in jobs:
		context = job_context.get(job.name, {})
		job.customer_site = next(iter(context.get("sites") or []), None)
		job.equipment_count = len(context.get("equipment") or [])
	requests = frappe.get_list("Service Request", filters={"customer": customer}, fields=["name", "subject", "service_type", "status", "preferred_start", "creation"], order_by="creation desc", limit=200)
	maintenance = frappe.get_list("Maintenance Occurrence", filters={"customer": customer, "status": ["not in", ["Cancelled", "Skipped"]]}, fields=["name", "installed_equipment", "customer_site", "service_type", "due_date", "status", "released_job"], order_by="due_date asc", limit=500)
	contracts = frappe.get_list("Service Contract", filters={"customer": customer}, fields=["name", "status", "start_date", "end_date", "included_visits", "renewal_recommended", "renewal_quotation"], order_by="end_date asc", limit=100)
	reports = frappe.get_list("Service Report", filters={"customer": customer, "status": "Submitted"}, fields=["name", "service_job", "report_type", "revision", "submitted_on"], order_by="submitted_on desc", limit=200)
	certificates = frappe.get_list("Service Certificate", filters={"customer": customer, "status": "Issued"}, fields=["name", "service_job", "installed_equipment", "certificate_type", "revision", "issued_on"], order_by="issued_on desc", limit=200)
	quotations = _native_documents("Quotation", job_names, ["name", "transaction_date", "status", "grand_total", "currency", "valid_till", "fsm_service_job"])
	invoices = _native_documents("Sales Invoice", job_names, ["name", "posting_date", "status", "grand_total", "outstanding_amount", "currency", "due_date", "fsm_service_job"])
	today = nowdate()
	upcoming = [row for row in maintenance if row.status in {"Forecast", "Due", "Released"} and str(row.due_date) >= today]
	overdue = [row for row in maintenance if row.status == "Overdue" or (row.status in {"Forecast", "Due"} and str(row.due_date) < today)]
	renewals = [row for row in contracts if row.status in {"Active", "Expired"} and str(row.end_date) <= add_days(today, 60)]
	service_names = sorted({
		str(row.service_type) for row in [*jobs, *requests, *maintenance]
		if row.get("service_type")
	})
	calendar = []
	jobs_by_name = {row.name: row for row in jobs}
	for visit in visits:
		job = jobs_by_name.get(visit.service_job, {})
		context = job_context.get(visit.service_job, {})
		calendar.append({
			"type": "visit", "name": visit.name, "service_job": visit.service_job,
			"start": visit.scheduled_start, "end": visit.scheduled_end, "status": visit.status,
			"title": job.get("service_type") or visit.service_job,
			"site": job.get("customer_site"), "team": visit.service_team,
			"technician": visit.primary_technician,
			"equipment": next(iter(context.get("equipment") or []), None),
			"equipment_count": len(context.get("equipment") or []),
		})
	maintenance_groups = {}
	for occurrence in maintenance:
		key = (
			occurrence.due_date, occurrence.customer_site, occurrence.service_type,
			occurrence.status, occurrence.released_job,
		)
		group = maintenance_groups.setdefault(key, {
			"type": "maintenance", "name": occurrence.name, "service_job": occurrence.released_job,
			"start": occurrence.due_date, "end": occurrence.due_date, "status": occurrence.status,
			"title": occurrence.service_type or "Preventive Maintenance",
			"site": occurrence.customer_site, "equipment": occurrence.installed_equipment,
			"equipment_count": 0,
		})
		group["equipment_count"] += 1
	calendar.extend(maintenance_groups.values())
	return {
		"dashboard": {"sites": frappe.db.count("Customer Site", {"customer": customer, "status": "Active"}), "equipment": frappe.db.count("Installed Equipment", {"customer": customer}), "open_jobs": sum(row.status not in {"Completed", "Cancelled"} for row in jobs), "upcoming_maintenance": len(upcoming), "overdue_maintenance": len(overdue), "active_contracts": sum(row.status == "Active" for row in contracts)},
		"requests": requests, "jobs": jobs, "service_history": [row for row in jobs if row.status in {"Completed", "Cancelled"}],
		"upcoming_maintenance": upcoming, "overdue_maintenance": overdue, "contracts": contracts, "renewals": renewals,
		"reports": reports, "certificates": certificates, "quotations": quotations, "invoices": invoices,
		"visits": visits, "items": items, "services": service_names,
		"calendar": sorted(calendar, key=lambda row: str(row.get("start") or "")),
	}


def _native_documents(doctype: str, jobs: list[str], fields: list[str]):
	if not jobs or not frappe.get_meta(doctype).has_field("fsm_service_job"):
		return []
	# Root Job ownership was established above; fields are a fixed customer-safe projection.
	return frappe.get_all(doctype, filters={"fsm_service_job": ["in", jobs]}, fields=fields, order_by="creation desc", limit=200)
