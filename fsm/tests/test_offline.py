import uuid

import frappe

from fsm.offline import sync_commands
from fsm.tests.test_security import SecurityFixture


class TestOfflineCommandIngress(SecurityFixture):
	def command(self, job, command_id=None, expected_version=None):
		return {
			"command_id": command_id or str(uuid.uuid4()),
			"entity_type": "Service Job",
			"entity_id": job,
			"expected_version": expected_version or str(frappe.db.get_value("Service Job", job, "modified")),
			"action": "job.complete",
			"payload": {},
		}

	def test_successful_command_is_idempotent(self):
		frappe.set_user(self.technician_user_a)
		row = self.command(self.job_a)
		first = sync_commands([row])["results"][0]
		second = sync_commands([row])["results"][0]
		self.assertEqual(first["state"], "Synced")
		self.assertEqual(second["state"], "Synced")
		self.assertEqual(frappe.db.count("Mobile Command Receipt", {"command_id": row["command_id"]}), 1)

	def test_stale_version_returns_conflict_without_mutation(self):
		frappe.set_user(self.technician_user_a)
		result = sync_commands([self.command(self.job_a, expected_version="stale")])["results"][0]
		self.assertEqual(result["state"], "Conflict")
		self.assertEqual(frappe.db.get_value("Service Job", self.job_a, "status"), "In Progress")

	def test_cross_company_command_fails_inside_guard(self):
		frappe.set_user(self.technician_user_a)
		result = sync_commands([self.command(self.job_b)])["results"][0]
		self.assertEqual(result["state"], "Failed")
		self.assertEqual(frappe.db.get_value("Service Job", self.job_b, "status"), "In Progress")

	def test_customer_cannot_use_mobile_command_ingress(self):
		frappe.set_user(self.customer_user_a)
		with self.assertRaises(frappe.PermissionError):
			sync_commands([self.command(self.job_a)])
