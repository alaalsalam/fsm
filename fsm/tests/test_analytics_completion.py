from __future__ import annotations

import frappe

from fsm.analytics import domain_dashboard
from fsm.tests.test_security import SecurityFixture


class TestAnalyticsCompletion(SecurityFixture):
	def test_manager_dashboard_is_company_scoped(self):
		frappe.set_user(self.manager_a)
		result = domain_dashboard(90)
		self.assertEqual(result["company"], self.company_a)
		self.assertEqual(result["operations"]["total_jobs"], 1)
		self.assertEqual(result["executive"]["customers"], 1)
		self.assertEqual(result["teams"][0]["jobs"], 1)

	def test_other_company_has_independent_projection(self):
		frappe.set_user(self.manager_b)
		result = domain_dashboard(90)
		self.assertEqual(result["company"], self.company_b)
		self.assertEqual(result["operations"]["total_jobs"], 1)
		self.assertNotEqual(result["company"], self.company_a)

	def test_non_manager_cannot_read_business_analytics(self):
		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.PermissionError):
			domain_dashboard(90)
