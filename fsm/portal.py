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
		fields=["name", "status", "phase", "service_type", "scheduled_date", "completed_on", "coverage_status", "service_contract", "quotation", "sales_invoice"],
		order_by="creation desc",
		limit=500,
	)
	job_names = [row.name for row in jobs]
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
	return {
		"dashboard": {"sites": frappe.db.count("Customer Site", {"customer": customer, "status": "Active"}), "equipment": frappe.db.count("Installed Equipment", {"customer": customer}), "open_jobs": sum(row.status not in {"Completed", "Cancelled"} for row in jobs), "upcoming_maintenance": len(upcoming), "overdue_maintenance": len(overdue), "active_contracts": sum(row.status == "Active" for row in contracts)},
		"requests": requests, "jobs": jobs, "service_history": [row for row in jobs if row.status in {"Completed", "Cancelled"}],
		"upcoming_maintenance": upcoming, "overdue_maintenance": overdue, "contracts": contracts, "renewals": renewals,
		"reports": reports, "certificates": certificates, "quotations": quotations, "invoices": invoices,
	}


def _native_documents(doctype: str, jobs: list[str], fields: list[str]):
	if not jobs or not frappe.get_meta(doctype).has_field("fsm_service_job"):
		return []
	# Root Job ownership was established above; fields are a fixed customer-safe projection.
	return frappe.get_all(doctype, filters={"fsm_service_job": ["in", jobs]}, fields=fields, order_by="creation desc", limit=200)
