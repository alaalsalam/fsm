from __future__ import annotations

import frappe

from fsm.portal import get_my_portal_hub
from fsm.tests.test_security import SecurityFixture


class TestPortalCompletion(SecurityFixture):
	def test_customer_hub_isolated_and_safe(self):
		frappe.set_user(self.customer_user_a)
		hub = get_my_portal_hub()
		self.assertIn(self.job_a, [row.name for row in hub["jobs"]])
		self.assertNotIn(self.job_b, [row.name for row in hub["jobs"]])
		self.assertIn(self.request_a, [row.name for row in hub["requests"]])
		self.assertNotIn(self.request_b, [row.name for row in hub["requests"]])
		for row in hub["jobs"]:
			self.assertNotIn("total_cost", row)
			self.assertNotIn("materials_cost", row)
			self.assertNotIn("notes", row)

	def test_guest_is_denied(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.AuthenticationError):
			get_my_portal_hub()

	def test_dashboard_counts_only_owned_roots(self):
		frappe.set_user(self.customer_user_a)
		hub_a = get_my_portal_hub()
		frappe.set_user(self.customer_user_b)
		hub_b = get_my_portal_hub()
		self.assertEqual(hub_a["dashboard"]["open_jobs"], 1)
		self.assertEqual(hub_b["dashboard"]["open_jobs"], 1)
		self.assertEqual(len(hub_a["jobs"]), 1)
		self.assertEqual(len(hub_b["jobs"]), 1)
