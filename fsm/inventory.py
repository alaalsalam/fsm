# Copyright (c) 2026, DIGIT and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from fsm.security.policy import require_authenticated, require_company_scope, require_role
from fsm.security.scopes import FSM_MANAGER, FSM_TECHNICIAN, SYSTEM_MANAGER, current_technician, user_roles


@frappe.whitelist()
def get_stock_levels(
	warehouse: str | None = None,
	technician: str | None = None,
	item: str | None = None,
	low_only: int = 0,
):
	"""
	Stock levels for FSM warehouses, each row flagged `low` against its reorder level.

	- warehouse: restrict to one warehouse.
	- technician: restrict to that technician's van warehouse.
	- item: restrict to one item.
	- low_only: when truthy, only return rows at or below their reorder point.
	"""
	user = require_authenticated()
	roles = user_roles(user)
	technician_only = FSM_TECHNICIAN in roles and not ({FSM_MANAGER, SYSTEM_MANAGER} & roles)
	if technician_only:
		own_technician = current_technician(user)
		if technician and technician != own_technician:
			frappe.throw(_("You can only view your own van stock."), frappe.PermissionError)
		technician = own_technician
	if technician:
		technician_values = frappe.db.get_value(
			"Technician", technician, ["warehouse", "company"], as_dict=True
		)
		if not technician_values:
			frappe.throw(_("Technician not found."))
		if technician_only:
			# A technician's stock view is exactly their van warehouse — never a
			# caller-supplied warehouse and never the all-warehouses fallback.
			if not technician_values.warehouse:
				return []
			warehouse = technician_values.warehouse
		else:
			warehouse = technician_values.warehouse or warehouse
		if FSM_MANAGER in roles and SYSTEM_MANAGER not in roles:
			require_company_scope(technician_values.company, user)
	if not ({FSM_MANAGER, FSM_TECHNICIAN, SYSTEM_MANAGER} & roles):
		frappe.throw(_("You are not permitted to view stock."), frappe.PermissionError)
	if warehouse and FSM_MANAGER in roles and SYSTEM_MANAGER not in roles:
		require_company_scope(frappe.db.get_value("Warehouse", warehouse, "company"), user)
	warehouses = [warehouse] if warehouse else _fsm_warehouses()
	if not warehouses:
		return []

	filters = {"warehouse": ["in", warehouses]}
	if item:
		filters["item_code"] = item

	bins = frappe.get_all(
		"Bin",
		filters=filters,
		fields=["item_code", "warehouse", "actual_qty", "reserved_qty", "projected_qty"],
		order_by="item_code asc",
	)

	item_codes = {row.item_code for row in bins}
	item_names = {
		row.name: row.item_name
		for row in frappe.get_all(
			"Item", filters={"name": ["in", sorted(item_codes)]}, fields=["name", "item_name"]
		)
	}
	reorder_levels = {
		(row.parent, row.warehouse): row.warehouse_reorder_level
		for row in frappe.get_all(
			"Item Reorder",
			filters={"parent": ["in", sorted(item_codes)], "warehouse": ["in", warehouses]},
			fields=["parent", "warehouse", "warehouse_reorder_level"],
		)
	}
	rows = []
	for b in bins:
		reorder = reorder_levels.get((b.item_code, b.warehouse))
		low = _is_low(b.actual_qty, reorder)
		if low_only and not low:
			continue
		rows.append(
			{
				"item_code": b.item_code,
				"item_name": item_names.get(b.item_code),
				"warehouse": b.warehouse,
				"actual_qty": b.actual_qty,
				"reserved_qty": b.reserved_qty,
				"projected_qty": b.projected_qty,
				"reorder_level": reorder,
				"low": low,
			}
		)
	return rows


@frappe.whitelist()
def get_van_stock(technician: str | None = None):
	"""Stock on the signed-in technician's van (or a given technician's)."""
	if not technician:
		roles = user_roles()
		if FSM_TECHNICIAN in roles and not ({FSM_MANAGER, SYSTEM_MANAGER} & roles):
			technician = current_technician()
		else:
			require_role(FSM_MANAGER, SYSTEM_MANAGER)
			frappe.throw(_("Select a technician."))
	warehouse = frappe.db.get_value("Technician", technician, "warehouse")
	if not warehouse:
		return []
	return get_stock_levels(warehouse=warehouse)


def low_stock_rows() -> list[dict]:
	"""Every FSM-warehouse item currently at or below its reorder point."""
	out = []
	for wh in _fsm_warehouses():
		out.extend(get_stock_levels(warehouse=wh, low_only=1))
	return out


def _fsm_warehouses() -> list[str]:
	"""Warehouses field service cares about: every technician van + the default."""
	roles = user_roles()
	filters = {"warehouse": ["is", "set"]}
	if FSM_MANAGER in roles and SYSTEM_MANAGER not in roles:
		from fsm.security.scopes import allowed_companies

		filters["company"] = ["in", sorted(allowed_companies() or set())]
	elif FSM_TECHNICIAN in roles and SYSTEM_MANAGER not in roles:
		filters["name"] = current_technician()
	vans = frappe.get_all(
		"Technician",
		filters=filters,
		pluck="warehouse",
	)
	default = frappe.db.get_single_value("Service Settings", "default_warehouse")
	if default and (SYSTEM_MANAGER in roles or default in vans):
		vans.append(default)
	return sorted({w for w in vans if w})


def _is_low(actual_qty: float, reorder_level: float | None) -> bool:
	"""Low when below the ERPNext reorder level, else below the Service Settings
	fallback threshold (when one is configured)."""
	if reorder_level is not None:
		return (actual_qty or 0) <= reorder_level
	threshold = frappe.db.get_single_value("Service Settings", "low_stock_threshold") or 0
	return bool(threshold) and (actual_qty or 0) <= threshold
