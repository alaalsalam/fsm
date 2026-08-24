# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from fsm.security.policy import require_authenticated, require_job_access, validate_allowed_fields

RETURN_ITEM_FIELDS = {"item_code", "qty", "disposition", "note"}


@frappe.whitelist()
def create_return(service_job: str, items, warehouse: str | None = None, reason: str | None = None):
	"""Create a Service Return (submitted for approval) from a job's returned parts."""
	rows = json.loads(items) if isinstance(items, str) else items
	if not rows:
		frappe.throw(_("Add at least one item to return."))
	require_job_access(service_job, "write")
	for row in rows:
		validate_allowed_fields(row, RETURN_ITEM_FIELDS)
	doc = frappe.get_doc(
		{
			"doctype": "Service Return",
			"service_job": service_job,
			"warehouse": warehouse,
			"reason": reason,
			"items": [
				{
					"item_code": r["item_code"],
					"qty": r["qty"],
					"disposition": r.get("disposition", "Restock"),
					"note": r.get("note"),
				}
				for r in rows
			],
		}
	)
	doc.insert()
	doc.save()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def list_returns(status: str | None = None, job: str | None = None):
	require_authenticated()
	filters = {}
	if status:
		filters["status"] = status
	if job:
		filters["service_job"] = job
	return frappe.get_list(
		"Service Return",
		filters=filters,
		fields=["name", "service_job", "customer", "status", "return_date", "warehouse", "stock_entry"],
		order_by="creation desc",
	)


@frappe.whitelist()
def get_return(name: str):
	doc = frappe.get_doc("Service Return", name)
	require_job_access(doc.service_job, "read")
	return {
		"name": doc.name,
		"service_job": doc.service_job,
		"customer": doc.customer,
		"status": doc.status,
		"return_date": doc.return_date,
		"warehouse": doc.warehouse,
		"stock_entry": doc.stock_entry,
		"reason": doc.reason,
		"items": [
			{
				"item_code": i.item_code,
				"item_name": i.item_name,
				"qty": i.qty,
				"disposition": i.disposition,
				"note": i.note,
			}
			for i in doc.items
		],
	}


@frappe.whitelist()
def process_return(name: str, action: str):
	"""Advance a return: action in (approve, receive, close)."""
	doc = frappe.get_doc("Service Return", name)
	require_job_access(doc.service_job, "write", manager_only=True)
	handler = {"approve": doc.approve, "receive": doc.receive, "close": doc.close}.get(action)
	if not handler:
		frappe.throw(_("Unknown action {0}.").format(action))
	handler()
	return {"name": doc.name, "status": doc.status, "stock_entry": doc.stock_entry}
