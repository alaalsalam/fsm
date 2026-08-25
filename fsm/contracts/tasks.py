from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate, nowdate

from fsm.contracts.commands import transition_contract


def update_contract_statuses():
	"""Daily retry-safe projection for expiry and renewal flags."""
	today = getdate(nowdate())
	soon = getdate(add_days(today, 30))
	for name in frappe.get_all(
		"Service Contract", filters={"status": ["in", ["Active", "Suspended"]]}, pluck="name"
	):
		doc = frappe.get_doc("Service Contract", name)
		if getdate(doc.end_date) < today:
			transition_contract(doc.name, "Expired", "Contract period ended", source="Scheduler")
			continue
		expiring = int(getdate(doc.end_date) <= soon)
		if doc.expiring_soon != expiring or (expiring and not doc.renewal_recommended):
			doc.flags.fsm_command = True
			doc.expiring_soon = expiring
			if expiring:
				doc.renewal_recommended = 1
			doc.save()
