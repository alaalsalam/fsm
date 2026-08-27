from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from fsm.process.completion import completion_blockers
from fsm.process.maintenance_flow import create_maintenance_plans_from_contract
from fsm.service_operations.commands import create_job_from_request
from fsm.tests.test_installed_base import _customer, _item, _manual_equipment, _site
from fsm.tests.test_service_contracts import _contract


class TestFlowGateIntegration(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.customer = _customer("FLOW Customer")
		self.site = _site(self.customer, company=self.company, label="FLOW")
		self.equipment = _manual_equipment(
			self.customer, _item(warranty_days=365), self.site.name, self.company
		)

	def test_contract_to_pm_preview_and_create_are_idempotent(self):
		contract = _contract(
			self.company,
			self.customer,
			site=self.site.name,
			equipment=self.equipment.name,
		)
		preview = create_maintenance_plans_from_contract(contract.name)
		self.assertTrue(preview["preview"])
		self.assertTrue(preview["requires_cadence_confirmation"])
		self.assertEqual(preview["proposals"][0]["equipment_count"], 1)

		created = create_maintenance_plans_from_contract(
			contract.name, service_type="Preventive Maintenance", preview=0
		)
		retry = create_maintenance_plans_from_contract(
			contract.name, service_type="Preventive Maintenance", preview=0
		)
		self.assertTrue(created["plans"][0]["created"])
		self.assertFalse(retry["plans"][0]["created"])
		self.assertEqual(created["plans"][0]["maintenance_plan"], retry["plans"][0]["maintenance_plan"])

	def test_next_action_completion_policy_is_service_type_driven(self):
		settings = frappe.get_single("Service Settings")
		before = settings.report_required_service_types
		try:
			settings.report_required_service_types = "Flow Mandatory Report"
			settings.save(ignore_permissions=True)
			request = frappe.get_doc(
				{
					"doctype": "Service Request",
					"company": self.company,
					"customer": self.customer,
					"subject": "FLOW report policy",
					"service_type": "Flow Mandatory Report",
					"status": "Open",
					"source": "Manual",
				}
			)
			request.flags.fsm_command = True
			request.insert(ignore_permissions=True)
			job = create_job_from_request(request.name, "flow-report-policy")
			self.assertIn("SERVICE_REPORT_REQUIRED", {row["code"] for row in completion_blockers(job)})
		finally:
			settings.report_required_service_types = before
			settings.save(ignore_permissions=True)
