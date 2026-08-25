import uuid

import frappe

from fsm.offline import sync_commands
from fsm.reporting import generate_service_report, transition_service_report
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

	def test_same_batch_sequence_shares_pre_batch_version(self):
		"""An offline queue captured against one snapshot legitimately carries the
		same expected_version on sequential commands; after the first mutation the
		rest of the SAME batch must not self-conflict (mobile signature flow)."""
		frappe.set_user("Administrator")
		report = generate_service_report(self.job_a)
		transition_service_report(report["name"], "Generated")
		transition_service_report(report["name"], "Customer Review")
		pre_batch = str(frappe.db.get_value("Service Report", report["name"], "modified"))

		frappe.set_user(self.technician_user_a)
		batch = [
			{
				"command_id": str(uuid.uuid4()),
				"entity_type": "Service Report",
				"entity_id": report["name"],
				"expected_version": pre_batch,
				"action": "report.update",
				"payload": {"customer_signature": "data:image/png;base64,c2ln"},
			},
			{
				"command_id": str(uuid.uuid4()),
				"entity_type": "Service Report",
				"entity_id": report["name"],
				"expected_version": pre_batch,
				"action": "report.transition",
				"payload": {"status": "Customer Signed"},
			},
		]
		results = sync_commands(batch)["results"]
		self.assertEqual([r["state"] for r in results], ["Synced", "Synced"])
		self.assertEqual(
			frappe.db.get_value("Service Report", report["name"], "status"), "Customer Signed"
		)

	def test_external_edit_still_conflicts_across_batches(self):
		"""The chain exemption is batch-local: a version captured before an edit
		that happened OUTSIDE the batch still returns Conflict."""
		frappe.set_user("Administrator")
		report = generate_service_report(self.job_a, generation_key="hardening-conflict")
		transition_service_report(report["name"], "Generated")
		transition_service_report(report["name"], "Customer Review")
		stale = str(frappe.db.get_value("Service Report", report["name"], "modified"))
		frappe.db.set_value("Service Report", report["name"], "work_performed", "external edit")

		frappe.set_user(self.technician_user_a)
		result = sync_commands(
			[
				{
					"command_id": str(uuid.uuid4()),
					"entity_type": "Service Report",
					"entity_id": report["name"],
					"expected_version": stale,
					"action": "report.transition",
					"payload": {"status": "Customer Signed"},
				}
			]
		)["results"][0]
		self.assertEqual(result["state"], "Conflict")
