# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from fsm.security.policy import require_authenticated, require_job_access, validate_allowed_fields
from fsm.service_operations.events import append_event

RETURN_ITEM_FIELDS = {"item_code", "qty", "disposition", "note"}
WORKSHOP_FIELDS = {
	"pickup_date",
	"pickup_address",
	"warehouse",
	"quotation",
	"sales_invoice",
	"customer_approval",
	"repair_notes",
	"testing_result",
	"quality_result",
	"final_outcome",
	"reason",
	"notes",
}
TRANSITIONS = {
	"Pickup Requested": {"Picked Up", "Cancelled"},
	"Picked Up": {"Workshop Received", "Cancelled"},
	"Workshop Received": {"Initial Inspection", "Cancelled"},
	"Initial Inspection": {"Estimate Required", "Repair In Progress", "Cancelled"},
	"Estimate Required": {"Awaiting Customer Approval", "Cancelled"},
	"Awaiting Customer Approval": {"Repair In Progress", "Cancelled"},
	"Repair In Progress": {"Waiting Material", "Repair Completed", "Cancelled"},
	"Waiting Material": {"Repair In Progress", "Cancelled"},
	"Repair Completed": {"Testing", "Cancelled"},
	"Testing": {"Quality Inspection", "Repair In Progress", "Cancelled"},
	"Quality Inspection": {"Ready for Dispatch", "Repair In Progress", "Cancelled"},
	"Ready for Dispatch": {"Dispatched", "Cancelled"},
	"Dispatched": {"Reinstalled", "Cancelled"},
	"Reinstalled": {"Closed"},
	"Closed": set(),
	"Cancelled": set(),
}


def _items(items, *, required=True):
	rows = json.loads(items) if isinstance(items, str) else items
	rows = rows or []
	if required and not rows:
		frappe.throw(_("Add at least one item to return."))
	for row in rows:
		validate_allowed_fields(row, RETURN_ITEM_FIELDS)
		if not row.get("item_code") or float(row.get("qty") or 0) <= 0:
			frappe.throw(_("Return items require an Item and positive quantity."))
	return rows


def _return_doc(name: str, permission_type="read", *, manager_only=False):
	doc = frappe.get_doc("Service Return", name)
	require_job_access(doc.service_job, permission_type, manager_only=manager_only)
	return doc


@frappe.whitelist()
def create_return(service_job: str, items, warehouse: str | None = None, reason: str | None = None):
	"""Compatibility entry point; creates the canonical Pickup Requested RMA case."""
	rows = _items(items)
	job = require_job_access(service_job, "write")
	doc = _new_case(job, rows, warehouse=warehouse, reason=reason)
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
def create_workshop_case(
	service_job: str,
	installed_equipment: str,
	reason: str,
	items=None,
	warehouse: str | None = None,
	pickup_date: str | None = None,
	pickup_address: str | None = None,
):
	rows = _items(items, required=False)
	job = require_job_access(service_job, "write")
	if not any(row.installed_equipment == installed_equipment for row in job.equipment):
		frappe.throw(_("Installed Equipment must be linked to the Service Job."))
	doc = _new_case(
		job,
		rows,
		installed_equipment=installed_equipment,
		warehouse=warehouse,
		reason=reason,
		pickup_date=pickup_date,
		pickup_address=pickup_address,
	)
	return get_return(doc.name)


def _new_case(job, rows, **values):
	doc = frappe.get_doc(
		{
			"doctype": "Service Return",
			"service_job": job.name,
			"status": "Pickup Requested",
			**values,
			"items": [
				{
					"item_code": row["item_code"],
					"qty": row["qty"],
					"disposition": row.get("disposition", "Restock"),
					"note": row.get("note"),
				}
				for row in rows
			],
		}
	)
	doc.flags.fsm_command = True
	doc.insert(ignore_permissions=True)
	append_event("WorkshopCaseCreated", job, to_status=doc.status, source="Mobile", metadata={"service_return": doc.name})
	return doc


@frappe.whitelist()
def update_workshop_case(name: str, **values):
	validate_allowed_fields(values, WORKSHOP_FIELDS)
	doc = _return_doc(name, "write")
	if doc.status in {"Closed", "Cancelled"}:
		frappe.throw(_("Terminal Workshop/RMA cases are immutable."))
	if {"quotation", "sales_invoice", "customer_approval"} & set(values):
		require_job_access(doc.service_job, "write", manager_only=True)
	if "customer_approval" in values:
		if values["customer_approval"] not in {"Pending", "Approved", "Rejected"}:
			frappe.throw(_("Invalid customer approval value."))
		doc.customer_approval_on = now_datetime() if values["customer_approval"] != "Pending" else None
	doc.update(values)
	doc.flags.fsm_command = True
	doc.save()
	append_event("WorkshopCaseUpdated", doc, source="Console", metadata={"fields": sorted(values)})
	return get_return(doc.name)


@frappe.whitelist()
def transition_workshop_case(name: str, status: str, reason: str | None = None):
	doc = _return_doc(name, "write")
	if status not in TRANSITIONS.get(doc.status, set()):
		frappe.throw(_("Invalid Workshop/RMA transition from {0} to {1}.").format(doc.status, status))
	_validate_transition(doc, status, reason)
	old = doc.status
	if status == "Workshop Received":
		doc.receive()
	else:
		doc.status = status
		doc.flags.fsm_command = True
		doc.save()
	append_event(
		"WorkshopCaseStatusChanged",
		doc,
		from_status=old,
		to_status=status,
		source="Mobile",
		metadata={"reason": reason, "outcome": doc.final_outcome},
	)
	return get_return(doc.name)


def _validate_transition(doc, status: str, reason: str | None):
	if status == "Workshop Received" and not doc.warehouse:
		frappe.throw(_("Set the Workshop Warehouse before receipt."))
	if status == "Awaiting Customer Approval" and not doc.quotation:
		frappe.throw(_("Link an ERPNext Quotation before customer approval."))
	if status == "Repair In Progress" and doc.status == "Awaiting Customer Approval" and doc.customer_approval != "Approved":
		frappe.throw(_("Customer approval is required before repair."))
	if status == "Repair Completed" and not doc.repair_notes:
		frappe.throw(_("Record repair notes before completing repair."))
	if status == "Quality Inspection" and not doc.testing_result:
		frappe.throw(_("Record the testing result before quality inspection."))
	if status == "Ready for Dispatch" and doc.quality_result != "Pass":
		frappe.throw(_("Quality Inspection must pass before dispatch."))
	if status == "Closed" and not doc.final_outcome:
		frappe.throw(_("Select a final workshop outcome before closure."))
	if status == "Cancelled" and not reason:
		frappe.throw(_("A cancellation reason is required."))


@frappe.whitelist()
def list_returns(status: str | None = None, job: str | None = None):
	require_authenticated()
	filters = {}
	if status:
		filters["status"] = status
	if job:
		require_job_access(job, "read")
		filters["service_job"] = job
	return frappe.get_list(
		"Service Return",
		filters=filters,
		fields=[
			"name", "service_job", "installed_equipment", "customer", "status", "return_date",
			"warehouse", "stock_entry", "quotation", "sales_invoice", "customer_approval", "final_outcome",
		],
		order_by="creation desc",
	)


@frappe.whitelist()
def get_return(name: str):
	doc = _return_doc(name, "read")
	return {
		"name": doc.name,
		"service_job": doc.service_job,
		"installed_equipment": doc.installed_equipment,
		"customer": doc.customer,
		"status": doc.status,
		"return_date": doc.return_date,
		"pickup_date": doc.pickup_date,
		"pickup_address": doc.pickup_address,
		"warehouse": doc.warehouse,
		"stock_entry": doc.stock_entry,
		"quotation": doc.quotation,
		"sales_invoice": doc.sales_invoice,
		"customer_approval": doc.customer_approval,
		"customer_approval_on": doc.customer_approval_on,
		"repair_notes": doc.repair_notes,
		"testing_result": doc.testing_result,
		"quality_result": doc.quality_result,
		"final_outcome": doc.final_outcome,
		"reason": doc.reason,
		"notes": doc.notes,
		"items": [
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": row.qty,
				"disposition": row.disposition,
				"note": row.note,
			}
			for row in doc.items
		],
	}


@frappe.whitelist()
def process_return(name: str, action: str):
	"""Compatibility action names routed into the canonical Workshop/RMA lifecycle."""
	doc = _return_doc(name, "write", manager_only=True)
	target = {
		("Pickup Requested", "approve"): "Picked Up",
		("Picked Up", "receive"): "Workshop Received",
		("Reinstalled", "close"): "Closed",
	}.get((doc.status, action))
	if not target:
		frappe.throw(_("Unknown action {0} for state {1}.").format(action, doc.status))
	return transition_workshop_case(name, target)
