# Copyright (c) 2026, DIGIT and contributors
# For license information, please see license.txt

"""ERPNext-backed material planning and execution for Service Jobs.

FSM stores requirement intent on ``Service Job Item``. Stock truth remains in ERPNext
Bin, Material Request, Pick List, Stock Entry and Stock Ledger Entry records.
"""

from __future__ import annotations

import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from fsm.security.policy import require_job_access, validate_allowed_fields
from fsm.service_operations.events import append_event

MATERIAL_FIELDS = {"item_code", "qty", "installed_equipment", "uom", "serial_no", "batch_no"}
MOVEMENT_ACTIONS = {"Transfer", "Issue", "Consume", "Return"}


def _rows(items) -> list[dict]:
	rows = json.loads(items) if isinstance(items, str) else items
	if not isinstance(rows, list) or not rows:
		frappe.throw(_("Add at least one material item."), frappe.ValidationError)
	for row in rows:
		validate_allowed_fields(row, MATERIAL_FIELDS)
		if not row.get("item_code") or flt(row.get("qty")) <= 0:
			frappe.throw(_("Every material row needs an Item and a positive quantity."))
	return rows


def _context(job: str, service_visit: str | None, *, manager_only: bool = False):
	job_doc = require_job_access(job, "write", manager_only=manager_only)
	if service_visit and frappe.db.get_value("Service Visit", service_visit, "service_job") != job_doc.name:
		frappe.throw(_("Service Visit must belong to the Service Job."), frappe.ValidationError)
	return job_doc


def _validate_equipment(job_doc, rows: list[dict]) -> None:
	allowed = {row.installed_equipment for row in job_doc.equipment}
	for row in rows:
		equipment = row.get("installed_equipment")
		if equipment and equipment not in allowed:
			frappe.throw(_("Installed Equipment must be linked to the Service Job."), frappe.ValidationError)


def _team_warehouse(job_doc) -> str | None:
	if job_doc.assigned_service_team:
		warehouse = frappe.db.get_value("Service Team", job_doc.assigned_service_team, "default_warehouse")
		if warehouse:
			return warehouse
	if job_doc.primary_technician:
		warehouse = frappe.db.get_value("Technician", job_doc.primary_technician, "warehouse")
		if warehouse:
			return warehouse
	return frappe.db.get_single_value("Service Settings", "default_warehouse")


def _warehouse(job_doc, warehouse: str | None = None) -> str:
	warehouse = warehouse or _team_warehouse(job_doc)
	if not warehouse:
		frappe.throw(_("Set an ERPNext Warehouse on the Service Team, technician, or Service Settings."))
	values = frappe.db.get_value("Warehouse", warehouse, ["company", "is_group", "disabled"], as_dict=True)
	if not values or values.company != job_doc.company or values.is_group or values.disabled:
		frappe.throw(_("Select an active, non-group Warehouse for the Service Job company."))
	return warehouse


@frappe.whitelist()
def get_material_plan(job: str, service_visit: str | None = None, warehouse: str | None = None):
	"""Return requirements and state derived only from ERPNext stock documents."""
	job_doc = require_job_access(job, "read")
	if service_visit and frappe.db.get_value("Service Visit", service_visit, "service_job") != job_doc.name:
		frappe.throw(_("Service Visit must belong to the Service Job."), frappe.ValidationError)
	target = _warehouse(job_doc, warehouse)
	reserved = _picked_quantities(job_doc.name, target)
	movements = _movement_quantities(job_doc.name)
	result = []
	for row in job_doc.items:
		actual = flt(
			frappe.db.get_value("Bin", {"item_code": row.item_code, "warehouse": target}, "actual_qty")
		)
		key = (row.item_code, row.installed_equipment or "")
		required = flt(row.qty)
		row_reserved = min(flt(reserved.get(key)), required)
		available = max(actual - row_reserved, 0)
		result.append(
			{
				"requirement_row": row.name,
				"item_code": row.item_code,
				"item_name": row.item_name,
				"installed_equipment": row.installed_equipment,
				"material_type": row.material_type,
				"warehouse": target,
				"required_qty": required,
				"on_hand_qty": actual,
				"available_qty": available,
				"reserved_qty": row_reserved,
				"issued_qty": flt(movements["Issue"].get(key)),
				"consumed_qty": flt(movements["Consume"].get(key)),
				"returned_qty": flt(movements["Return"].get(key)),
				"shortage_qty": max(required - actual - row_reserved, 0),
			}
		)
	return {"job": job_doc.name, "service_visit": service_visit, "warehouse": target, "items": result}


@frappe.whitelist()
def request_shortage(
	job: str,
	items,
	service_visit: str | None = None,
	warehouse: str | None = None,
	schedule_date: str | None = None,
):
	"""Create a draft ERPNext Material Request for shortages; managers approve it natively."""
	rows = _rows(items)
	job_doc = _context(job, service_visit, manager_only=True)
	_validate_equipment(job_doc, rows)
	target = _warehouse(job_doc, warehouse)
	mr = frappe.new_doc("Material Request")
	mr.company = job_doc.company
	mr.material_request_type = "Material Transfer"
	mr.transaction_date = nowdate()
	mr.schedule_date = schedule_date or nowdate()
	mr.fsm_service_job = job_doc.name
	mr.fsm_service_visit = service_visit
	for row in rows:
		mr.append(
			"items",
			{
				"item_code": row["item_code"],
				"qty": row["qty"],
				"uom": row.get("uom"),
				"schedule_date": mr.schedule_date,
				"warehouse": target,
				"fsm_installed_equipment": row.get("installed_equipment"),
			},
		)
	# Authorization is established above; stock workflow roles need not be granted to FSM users.
	mr.insert(ignore_permissions=True)
	append_event("MaterialShortageRequested", job_doc, source="Console", metadata={"material_request": mr.name})
	return {"name": mr.name, "status": mr.status, "warehouse": target}


@frappe.whitelist()
def reserve_materials(
	job: str,
	items,
	service_visit: str | None = None,
	warehouse: str | None = None,
):
	"""Create a submitted ERPNext Pick List as the auditable operational reservation."""
	rows = _rows(items)
	job_doc = _context(job, service_visit, manager_only=True)
	_validate_equipment(job_doc, rows)
	source = _warehouse(job_doc, warehouse)
	pick = frappe.new_doc("Pick List")
	pick.company = job_doc.company
	pick.purpose = "Material Transfer"
	pick.pick_manually = 1
	pick.fsm_service_job = job_doc.name
	pick.fsm_service_visit = service_visit
	for row in rows:
		stock_uom = frappe.db.get_value("Item", row["item_code"], "stock_uom")
		qty = flt(row["qty"])
		on_hand = flt(
			frappe.db.get_value("Bin", {"item_code": row["item_code"], "warehouse": source}, "actual_qty")
		)
		if on_hand < qty:
			frappe.throw(
				_("Only {0} of {1} is available in {2}.").format(on_hand, row["item_code"], source)
			)
		pick.append(
			"locations",
			{
				"item_code": row["item_code"],
				"warehouse": source,
				"qty": qty,
				"stock_qty": qty,
				"picked_qty": qty,
				"uom": row.get("uom") or stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1,
				"serial_no": row.get("serial_no"),
				"batch_no": row.get("batch_no"),
				"fsm_installed_equipment": row.get("installed_equipment"),
			},
		)
	pick.flags.ignore_permissions = True
	pick.insert()
	pick.submit()
	append_event("MaterialsReserved", job_doc, source="Console", metadata={"pick_list": pick.name})
	return {"name": pick.name, "status": pick.status, "warehouse": source}


@frappe.whitelist()
def post_material_movement(
	job: str,
	action: str,
	items,
	service_visit: str | None = None,
	source_warehouse: str | None = None,
	target_warehouse: str | None = None,
):
	"""Post issue/consumption/return using a submitted ERPNext Stock Entry."""
	if action not in MOVEMENT_ACTIONS:
		frappe.throw(_("Invalid material action."), frappe.ValidationError)
	rows = _rows(items)
	job_doc = _context(job, service_visit, manager_only=action != "Consume")
	_validate_equipment(job_doc, rows)
	team_warehouse = _warehouse(job_doc)
	if action == "Consume":
		source = _warehouse(job_doc, source_warehouse or team_warehouse)
		target = None
		purpose = "Material Issue"
	elif action == "Return":
		if not target_warehouse:
			frappe.throw(_("Select the Warehouse receiving the unused material."))
		source = _warehouse(job_doc, source_warehouse or team_warehouse)
		target = _warehouse(job_doc, target_warehouse)
		purpose = "Material Transfer"
	else:
		if not source_warehouse:
			frappe.throw(_("Select the source Warehouse."))
		source = _warehouse(job_doc, source_warehouse)
		target = _warehouse(job_doc, target_warehouse or team_warehouse)
		if source == target:
			frappe.throw(_("Source and target Warehouses must differ."), frappe.ValidationError)
		purpose = "Material Transfer"
	se = frappe.new_doc("Stock Entry")
	se.company = job_doc.company
	se.stock_entry_type = purpose
	se.purpose = purpose
	se.fsm_service_job = job_doc.name
	se.fsm_service_visit = service_visit
	se.fsm_material_action = action
	for row in rows:
		stock_uom = frappe.db.get_value("Item", row["item_code"], "stock_uom")
		se.append(
			"items",
			{
				"item_code": row["item_code"],
				"qty": row["qty"],
				"uom": row.get("uom") or stock_uom,
				"stock_uom": stock_uom,
				"conversion_factor": 1,
				"s_warehouse": source,
				"t_warehouse": target,
				"serial_no": row.get("serial_no"),
				"batch_no": row.get("batch_no"),
				"fsm_installed_equipment": row.get("installed_equipment"),
			},
		)
	se.set_missing_values()
	se.flags.ignore_permissions = True
	se.insert()
	se.submit()
	if action == "Consume":
		_recompute_material_cost(job_doc.name)
	append_event(
		{
			"Transfer": "MaterialsTransferred",
			"Issue": "MaterialsIssued",
			"Consume": "MaterialsConsumed",
			"Return": "MaterialsReturned",
		}[action],
		job_doc,
		source="Mobile" if action == "Consume" else "Console",
		metadata={"stock_entry": se.name, "service_visit": service_visit},
	)
	return {"name": se.name, "status": "Submitted", "action": action, "purpose": purpose}


def consumed_material_cost(job: str) -> float | None:
	"""Actual consumed value from submitted ERPNext Stock Entries, or None if none exist."""
	parents = frappe.get_all(
		"Stock Entry",
		filters={"fsm_service_job": job, "fsm_material_action": "Consume", "docstatus": 1},
		pluck="name",
	)
	if not parents:
		return None
	rows = frappe.get_all(
		"Stock Entry Detail",
		filters={
			"parenttype": "Stock Entry",
			"parent": ["in", parents],
		},
		fields=["basic_amount"],
	)
	if not rows:
		return None
	return round(sum(abs(flt(row.basic_amount)) for row in rows), 2)


def _recompute_material_cost(job: str) -> None:
	doc = frappe.get_doc("Service Job", job)
	from fsm.costing import compute_costs

	doc.db_set(compute_costs(doc), update_modified=False)


def _picked_quantities(job: str, warehouse: str):
	totals = defaultdict(float)
	parents = frappe.get_all(
		"Pick List", filters={"fsm_service_job": job, "docstatus": 1}, pluck="name"
	)
	if not parents:
		return totals
	for row in frappe.get_all(
		"Pick List Item",
		filters={"parent": ["in", parents], "warehouse": warehouse},
		fields=["item_code", "picked_qty", "fsm_installed_equipment"],
	):
		totals[(row.item_code, row.fsm_installed_equipment or "")] += flt(row.picked_qty)
	return totals


def _movement_quantities(job: str):
	totals = {action: defaultdict(float) for action in MOVEMENT_ACTIONS}
	parents = frappe.get_all(
		"Stock Entry",
		filters={"fsm_service_job": job, "docstatus": 1},
		fields=["name", "fsm_material_action"],
	)
	if not parents:
		return totals
	actions = {row.name: row.fsm_material_action for row in parents}
	for row in frappe.get_all(
		"Stock Entry Detail",
		filters={"parent": ["in", list(actions)]},
		fields=["parent", "item_code", "qty", "fsm_installed_equipment"],
	):
		action = actions[row.parent]
		if action in totals:
			totals[action][(row.item_code, row.fsm_installed_equipment or "")] += flt(row.qty)
	return totals
