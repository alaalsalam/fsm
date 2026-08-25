from __future__ import annotations

import frappe

from fsm.commercial import (
	create_quotation_from_job,
	create_sales_invoice_from_job,
	get_billable_classification,
	get_payment_status,
	get_profitability,
	profitability_summary,
)
from fsm.contracts.commands import transition_contract
from fsm.tests.test_fire_safety import FireSafetyFixture
from fsm.tests.test_service_contracts import _contract


class TestCommercialIntegration(FireSafetyFixture):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		job = frappe.get_doc("Service Job", self.job_a)
		job.service_type = "Preventive Maintenance"
		job.append("items", {"item_code": self.equipment_a.item_code, "installed_equipment": self.equipment_a.name, "material_type": "Spare", "qty": 1, "rate": 125})
		job.append("items", {"item_code": self.equipment_a.item_code, "installed_equipment": self.equipment_a.name, "material_type": "Service", "qty": 1, "rate": 75})
		job.save()

	def _covered_contract(self):
		frappe.set_user("Administrator")
		contract = _contract(self.company_a, self.customer_a, site=self.site_a.name, equipment=self.equipment_a.name, classification="Partially Covered")
		transition_contract(contract.name, "Active")
		job = frappe.get_doc("Service Job", self.job_a)
		job.service_contract = contract.name
		job.flags.fsm_command = True
		job.save()
		return contract

	def test_chargeable_job_classifies_all_lines_billable(self):
		frappe.set_user(self.manager_a)
		result = get_billable_classification(self.job_a)
		self.assertEqual(len(result["lines"]), 2)
		self.assertEqual({row["classification"] for row in result["lines"]}, {"Billable"})
		self.assertEqual(result["billable_total"], 200)

	def test_partial_contract_covers_labour_but_not_parts(self):
		self._covered_contract()
		frappe.set_user(self.manager_a)
		result = get_billable_classification(self.job_a)
		by_component = {row["component"]: row["classification"] for row in result["lines"]}
		self.assertEqual(by_component["labour"], "Covered")
		self.assertEqual(by_component["parts"], "Billable")

	def test_quotation_is_native_billable_only_and_idempotent(self):
		self._covered_contract()
		frappe.set_user(self.manager_a)
		first = create_quotation_from_job(self.job_a)
		second = create_quotation_from_job(self.job_a)
		self.assertTrue(first["created"])
		self.assertEqual(first["name"], second["name"])
		quotation = frappe.get_doc("Quotation", first["name"])
		self.assertEqual(quotation.fsm_service_job, self.job_a)
		self.assertEqual(len(quotation.items), 1)
		self.assertEqual(quotation.items[0].rate, 125)

	def test_sales_invoice_and_payment_projection_remain_erpnext_owned(self):
		self._covered_contract()
		frappe.set_user(self.manager_a)
		first = create_sales_invoice_from_job(self.job_a)
		second = create_sales_invoice_from_job(self.job_a)
		self.assertEqual(first["name"], second["name"])
		invoice = frappe.get_doc("Sales Invoice", first["name"])
		self.assertEqual(invoice.fsm_service_job, self.job_a)
		self.assertEqual(len(invoice.items), 1)
		self.assertEqual(get_payment_status(self.job_a)["status"], "Draft")
		self.assertFalse(frappe.db.exists("DocType", "FSM Invoice"))

	def test_profitability_is_read_only_analytics(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Service Job", self.job_a, {"travel_cost": 10, "overhead_cost": 5})
		frappe.set_user(self.manager_a)
		row = get_profitability(self.job_a)
		self.assertEqual(row["travel_cost"], 10)
		self.assertEqual(row["gross_margin"], row["revenue"] - row["total_cost"])
		summary = profitability_summary(customer=self.customer_a)
		self.assertIn(self.job_a, [item["service_job"] for item in summary["rows"]])

	def test_company_scope_and_no_financial_duplicates(self):
		frappe.set_user(self.manager_b)
		with self.assertRaises(frappe.PermissionError):
			create_quotation_from_job(self.job_a)
		for doctype in ("FSM Payment", "FSM GL Entry", "FSM Invoice"):
			self.assertFalse(frappe.db.exists("DocType", doctype))
