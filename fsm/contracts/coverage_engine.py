from __future__ import annotations

import json

import frappe
from frappe.utils import flt, getdate, nowdate

from fsm.installed_base.warranty import get_equipment_warranty_status


def evaluate_coverage(
	service_job,
	installed_equipment: str | None = None,
	service_type: str | None = None,
	on_date: str | None = None,
) -> dict:
	"""Return a deterministic coverage decision without creating ERPNext commercial documents."""
	job = service_job if getattr(service_job, "doctype", None) else frappe.get_doc("Service Job", service_job)
	date = getdate(on_date or nowdate())
	equipment = _equipment_for_job(job, installed_equipment)
	requested_service = service_type or job.service_type or ""

	if equipment and get_equipment_warranty_status(equipment) == "Active":
		return _decision(
			"Warranty",
			"Equipment warranty is active on the service date.",
			labour=True,
			parts=True,
			travel=True,
			equipment=equipment.name,
		)

	contract = _resolve_contract(job, equipment, requested_service, date)
	if not contract:
		return _decision(
			"Chargeable",
			"No active warranty or matching Service Contract was found.",
			equipment=equipment.name if equipment else None,
		)

	rule = _matching_rule(contract, equipment, requested_service)
	if not rule:
		return _decision(
			"Not Covered",
			"The Contract has no active Coverage Rule for this service and equipment.",
			contract=contract.name,
			equipment=equipment.name if equipment else None,
		)

	entitlement = _matching_entitlement(contract, requested_service, date)
	if entitlement and flt(entitlement.remaining_quantity) <= 0:
		return _decision(
			"Not Covered",
			"The matching Contract entitlement has been exhausted.",
			contract=contract.name,
			equipment=equipment.name if equipment else None,
			entitlement=entitlement,
		)

	limits = json.loads(rule.limits_json) if rule.limits_json else {}
	return _decision(
		rule.classification,
		f"Matched Contract {contract.name} Coverage Rule {rule.rule_name}.",
		labour=bool(rule.labour),
		parts=bool(rule.parts),
		travel=bool(rule.travel),
		contract=contract.name,
		equipment=equipment.name if equipment else None,
		limits=limits,
		entitlement=entitlement,
		extra={
			"covered_consumables": bool(rule.consumables),
			"covered_refill": bool(rule.refill),
			"covered_inspection": bool(rule.inspection),
			"covered_workshop": bool(rule.workshop),
			"coverage_rule": rule.name,
		},
	)


def _equipment_for_job(job, installed_equipment: str | None):
	if not installed_equipment:
		return None
	if installed_equipment not in {row.installed_equipment for row in job.equipment}:
		frappe.throw("Installed Equipment is not linked to this Service Job.", frappe.ValidationError)
	return frappe.get_doc("Installed Equipment", installed_equipment)


def _resolve_contract(job, equipment, service_type: str, date):
	if job.service_contract:
		contract = frappe.get_doc("Service Contract", job.service_contract)
		return contract if _contract_matches(contract, job, equipment, date) else None

	names = frappe.get_all(
		"Service Contract",
		filters={
			"customer": job.customer,
			"company": job.company,
			"status": "Active",
			"start_date": ["<=", date],
			"end_date": [">=", date],
		},
		order_by="start_date desc, creation desc",
		pluck="name",
		limit=100,
	)
	for name in names:
		contract = frappe.get_doc("Service Contract", name)
		if _contract_matches(contract, job, equipment, date) and _matching_rule(
			contract, equipment, service_type
		):
			return contract
	return None


def _contract_matches(contract, job, equipment, date) -> bool:
	if (
		contract.customer != job.customer
		or contract.company != job.company
		or contract.status != "Active"
		or getdate(contract.start_date) > date
		or getdate(contract.end_date) < date
	):
		return False
	active_scope = [row for row in contract.covered_equipment if row.active]
	if not active_scope:
		return True
	job_sites = {row.customer_site for row in job.equipment if row.customer_site}
	if equipment:
		job_sites.add(equipment.customer_site)
	for row in active_scope:
		if row.installed_equipment and equipment and row.installed_equipment == equipment.name:
			return True
		if row.item_group and equipment and row.item_group == equipment.item_group and row.customer_site == equipment.customer_site:
			return True
		if not row.installed_equipment and not row.item_group and row.customer_site in job_sites:
			return True
	return False


def _matching_rule(contract, equipment, service_type: str):
	candidates = []
	for row in contract.coverage_rules:
		if not row.active:
			continue
		if row.service_type and row.service_type != service_type:
			continue
		if row.item_group and (not equipment or row.item_group != equipment.item_group):
			continue
		score = int(bool(row.service_type)) + int(bool(row.item_group))
		candidates.append((score, -row.idx, row))
	return max(candidates, default=(None, None, None), key=lambda item: (item[0], item[1]))[2]


def _matching_entitlement(contract, service_type: str, date):
	candidates = []
	for row in contract.entitlements:
		if not row.active or row.entitlement_type not in {"Visit", "Emergency Visit"}:
			continue
		if row.service_type and row.service_type != service_type:
			continue
		if row.period_start and getdate(row.period_start) > date:
			continue
		if row.period_end and getdate(row.period_end) < date:
			continue
		candidates.append((int(bool(row.service_type)), -row.idx, row))
	return max(candidates, default=(None, None, None), key=lambda item: (item[0], item[1]))[2]


def _decision(
	status: str,
	reason: str,
	*,
	labour: bool = False,
	parts: bool = False,
	travel: bool = False,
	contract: str | None = None,
	equipment: str | None = None,
	limits: dict | None = None,
	entitlement=None,
	extra: dict | None = None,
) -> dict:
	result = {
		"status": status,
		"reason": reason,
		"service_contract": contract,
		"installed_equipment": equipment,
		"covered_labour": labour,
		"covered_parts": parts,
		"covered_travel": travel,
		"limits": limits or {},
		"entitlement_row": entitlement.name if entitlement else None,
		"remaining_entitlement": flt(entitlement.remaining_quantity) if entitlement else None,
	}
	result.update(extra or {})
	return result
