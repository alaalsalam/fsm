from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from fsm.contracts.coverage_engine import evaluate_coverage
from fsm.costing import compute_costs
from fsm.security.policy import (
	bounded_int,
	require_job_access,
	require_manager_scope,
	resolve_manager_company,
)


def _component(row) -> str:
	return {"Spare": "parts", "Consumable": "consumables", "Refill": "refill"}.get(
		row.material_type, "labour"
	)


def classify_billable_lines(service_job: str):
	job = frappe.get_doc("Service Job", service_job)
	lines = []
	for row in job.items:
		decision = evaluate_coverage(job, row.installed_equipment or None)
		component = _component(row)
		covered = {
			"parts": decision.get("covered_parts"),
			"consumables": decision.get("covered_consumables"),
			"refill": decision.get("covered_refill"),
			"labour": decision.get("covered_labour"),
		}.get(component, False)
		billable = decision["status"] not in {"Warranty", "Contract Covered", "FOC"} and not covered
		lines.append({
			"row_name": row.name, "item_code": row.item_code, "installed_equipment": row.installed_equipment,
			"component": component, "qty": flt(row.qty), "rate": flt(row.rate), "amount": flt(row.amount),
			"classification": "Billable" if billable else "Covered", "coverage_status": decision["status"],
			"reason": decision["reason"],
		})
	return lines


def billable_item_rows(service_job: str):
	job = frappe.get_doc("Service Job", service_job)
	by_name = {row.name: row for row in job.items}
	return [by_name[line["row_name"]] for line in classify_billable_lines(service_job) if line["classification"] == "Billable"]


@frappe.whitelist()
def get_billable_classification(service_job: str):
	job = require_job_access(service_job, "read")
	lines = classify_billable_lines(job.name)
	return {
		"service_job": job.name, "coverage_status": job.coverage_status,
		"lines": lines, "billable_total": sum(line["amount"] for line in lines if line["classification"] == "Billable"),
		"covered_total": sum(line["amount"] for line in lines if line["classification"] == "Covered"),
	}


@frappe.whitelist()
def create_quotation_from_job(service_job: str):
	job = require_job_access(service_job, "write", manager_only=True)
	if job.quotation:
		return {"name": job.quotation, "created": False}
	rows = billable_item_rows(job.name)
	if not rows:
		frappe.throw(_("This Job has no billable lines requiring a Quotation."))
	doc = frappe.get_doc({
		"doctype": "Quotation", "quotation_to": "Customer", "party_name": job.customer, "company": job.company,
		"fsm_service_job": job.name,
		"items": [{"item_code": row.item_code, "qty": row.qty, "rate": row.rate, "uom": row.uom or None} for row in rows],
	})
	doc.insert(ignore_permissions=True)
	job.db_set("quotation", doc.name)
	return {"name": doc.name, "created": True}


@frappe.whitelist()
def create_sales_invoice_from_job(service_job: str):
	job = require_job_access(service_job, "write", manager_only=True)
	from fsm.field_service_management.doctype.service_job.service_job import make_invoice_from_job

	return {"name": make_invoice_from_job(job.name)}


@frappe.whitelist()
def get_payment_status(service_job: str):
	job = require_job_access(service_job, "read")
	if not job.sales_invoice:
		return {"sales_invoice": None, "status": "Not Invoiced", "grand_total": 0, "outstanding_amount": 0}
	invoice = frappe.db.get_value("Sales Invoice", job.sales_invoice, ["docstatus", "status", "grand_total", "outstanding_amount"], as_dict=True)
	if not invoice:
		return {"sales_invoice": job.sales_invoice, "status": "Missing", "grand_total": 0, "outstanding_amount": 0}
	status = "Draft" if invoice.docstatus == 0 else ("Paid" if flt(invoice.outstanding_amount) <= 0 else "Unpaid")
	return {"sales_invoice": job.sales_invoice, "status": status, "erpnext_status": invoice.status, "grand_total": flt(invoice.grand_total), "outstanding_amount": flt(invoice.outstanding_amount)}


def _profitability(job):
	costs = compute_costs(job)
	revenue = 0.0
	if job.sales_invoice:
		revenue = flt(frappe.db.get_value("Sales Invoice", job.sales_invoice, "grand_total"))
	elif job.status == "Completed":
		revenue = sum(line["amount"] for line in classify_billable_lines(job.name) if line["classification"] == "Billable")
	return {"service_job": job.name, "customer": job.customer, "service_contract": job.service_contract, "revenue": revenue, "labour_cost": flt(costs["labor_cost"]), "material_cost": flt(costs["materials_cost"]), "travel_cost": flt(costs["travel_cost"]), "total_cost": flt(costs["total_cost"]), "gross_margin": revenue - flt(costs["total_cost"])}


@frappe.whitelist()
def get_profitability(service_job: str):
	job = require_job_access(service_job, "read", manager_only=True)
	return _profitability(job)


@frappe.whitelist()
def profitability_summary(customer: str | None = None, service_contract: str | None = None, limit: int = 200):
	company = resolve_manager_company()
	require_manager_scope(company)
	filters = {"company": company}
	if customer:
		filters["customer"] = customer
	if service_contract:
		filters["service_contract"] = service_contract
	jobs = frappe.get_list("Service Job", filters=filters, pluck="name", limit=bounded_int(limit, 1, 1000))
	rows = [_profitability(frappe.get_doc("Service Job", name)) for name in jobs]
	return {"company": company, "rows": rows, "totals": {key: sum(row[key] for row in rows) for key in ("revenue", "labour_cost", "material_cost", "travel_cost", "total_cost", "gross_margin")}}
