from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint

from fsm.contracts.access import require_contract_access
from fsm.maintenance.commands import create_plan


def _contract_equipment(contract) -> dict[str, list[str]]:
	by_site: dict[str, set[str]] = defaultdict(set)
	for scope in contract.covered_equipment:
		if not scope.active:
			continue
		if scope.installed_equipment:
			by_site[scope.customer_site].add(scope.installed_equipment)
		else:
			filters = {
				"company": contract.company,
				"customer": contract.customer,
				"customer_site": scope.customer_site,
				"status": ["not in", ["Returned", "Replaced", "Disposed"]],
			}
			if scope.item_group:
				filters["item_group"] = scope.item_group
			by_site[scope.customer_site].update(
				frappe.get_all("Installed Equipment", filters=filters, pluck="name", limit=10000)
			)
	return {site: sorted(equipment) for site, equipment in by_site.items() if equipment}


@frappe.whitelist()
def create_maintenance_plans_from_contract(
	service_contract: str,
	service_type: str | None = None,
	interval_count: int = 1,
	interval_unit: str = "Months",
	first_due_date: str | None = None,
	timezone: str = "UTC",
	preview: int = 1,
):
	"""Preview or create one idempotent PM Plan per covered site.

	The cadence remains an explicit user decision because a Contract does not own a
	maintenance-frequency schema. Repeated execution reuses the existing Plan.
	"""
	contract = require_contract_access(service_contract, "write", manager_only=True)
	if contract.status not in {"Draft", "Active"}:
		frappe.throw(_("Only a Draft or Active Contract can seed Maintenance Plans."))
	if interval_unit not in {"Days", "Weeks", "Months", "Years"} or cint(interval_count) < 1:
		frappe.throw(_("Select a valid positive maintenance cadence."), frappe.ValidationError)

	by_site = _contract_equipment(contract)
	if not by_site:
		frappe.throw(_("The Contract has no active covered equipment to schedule."), frappe.ValidationError)

	service_type = (service_type or "").strip()
	proposals = []
	for site, equipment in sorted(by_site.items()):
		existing = frappe.db.get_value(
			"Maintenance Plan",
			{"service_contract": contract.name, "customer_site": site, "status": ["!=", "Cancelled"]},
			"name",
		)
		proposals.append(
			{
				"customer_site": site,
				"equipment": equipment,
				"equipment_count": len(equipment),
				"existing_plan": existing,
				"action": "Reuse" if existing else "Create Draft",
			}
		)

	if cint(preview):
		return {
			"preview": True,
			"service_contract": contract.name,
			"project": contract.project,
			"requires_cadence_confirmation": not bool(service_type),
			"proposals": proposals,
		}
	if not service_type:
		frappe.throw(_("Service Type must be confirmed before creating Maintenance Plans."))

	results = []
	for proposal in proposals:
		if proposal["existing_plan"]:
			results.append({"maintenance_plan": proposal["existing_plan"], "created": False})
			continue
		plan = create_plan(
			plan_title=f"{contract.contract_no or contract.name} - {proposal['customer_site']}",
			customer=contract.customer,
			company=contract.company,
			project=contract.project,
			customer_site=proposal["customer_site"],
			service_contract=contract.name,
			start_date=contract.start_date,
			end_date=contract.end_date,
			timezone=timezone,
			equipment=[{"installed_equipment": name, "active": 1} for name in proposal["equipment"]],
			lines=[
				{
					"line_code": "CONTRACT-PM",
					"service_type": service_type,
					"interval_count": cint(interval_count),
					"interval_unit": interval_unit,
					"first_due_date": first_due_date or contract.start_date,
					"equipment_scope": "All Plan Equipment",
					"active": 1,
				}
			],
		)
		results.append({"maintenance_plan": plan.name, "created": True})
	return {"preview": False, "service_contract": contract.name, "plans": results}
