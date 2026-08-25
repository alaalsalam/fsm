from __future__ import annotations

import json

import frappe

from fsm.reporting import (
	generate_service_report,
	get_service_certificate,
	issue_service_certificate,
	list_service_documents,
	revise_service_report,
	revoke_service_certificate,
	transition_service_report,
	update_service_report,
)
from fsm.tests.test_fire_safety import FireSafetyFixture


class TestServiceReporting(FireSafetyFixture):
	def _submitted_report(self):
		frappe.set_user(self.manager_a)
		doc = generate_service_report(self.job_a, generation_key=frappe.generate_hash())
		transition_service_report(doc.name, "Generated")
		transition_service_report(doc.name, "Customer Review")
		update_service_report(doc.name, customer_name="Test Customer", customer_signature="data:image/png;base64,AA==")
		transition_service_report(doc.name, "Customer Signed")
		transition_service_report(doc.name, "Verified")
		return transition_service_report(doc.name, "Submitted")

	def test_snapshot_contains_canonical_job_equipment_and_operations(self):
		frappe.set_user(self.technician_user_a)
		doc = generate_service_report(self.job_a, "Inspection Report", frappe.generate_hash())
		snapshot = json.loads(doc.snapshot)
		self.assertEqual(snapshot["job"]["name"], self.job_a)
		self.assertEqual(snapshot["equipment"][0]["installed_equipment"], self.equipment_a.name)
		self.assertIn("visits", snapshot)
		self.assertIn("materials", snapshot)

	def test_signature_or_refusal_is_required(self):
		frappe.set_user(self.technician_user_a)
		doc = generate_service_report(self.job_a, generation_key=frappe.generate_hash())
		transition_service_report(doc.name, "Generated")
		transition_service_report(doc.name, "Customer Review")
		with self.assertRaises(frappe.ValidationError):
			transition_service_report(doc.name, "Customer Signed")
		update_service_report(doc.name, signature_refused=1, refusal_reason="Customer unavailable")
		self.assertEqual(transition_service_report(doc.name, "Customer Signed").status, "Customer Signed")

	def test_submitted_report_is_immutable_and_revision_is_n_plus_one(self):
		source = self._submitted_report()
		with self.assertRaises(frappe.ValidationError):
			update_service_report(source.name, recommendations="changed")
		revision = revise_service_report(source.name, frappe.generate_hash())
		self.assertEqual(revision.revision, source.revision + 1)
		self.assertEqual(revision.supersedes, source.name)

	def test_generation_and_certificate_commands_are_idempotent(self):
		frappe.set_user(self.manager_a)
		key = frappe.generate_hash()
		first = generate_service_report(self.job_a, generation_key=key)
		second = generate_service_report(self.job_a, generation_key=key)
		self.assertEqual(first.name, second.name)
		report = self._submitted_report()
		certificate_key = frappe.generate_hash()
		first_cert = issue_service_certificate(report.name, "Refill Certificate", self.equipment_a.name, certificate_key)
		second_cert = issue_service_certificate(report.name, "Refill Certificate", self.equipment_a.name, certificate_key)
		self.assertEqual(first_cert.name, second_cert.name)

	def test_certificate_requires_submitted_report_and_can_be_revoked(self):
		frappe.set_user(self.manager_a)
		draft = generate_service_report(self.job_a, generation_key=frappe.generate_hash())
		with self.assertRaises(frappe.ValidationError):
			issue_service_certificate(draft.name, "Hydro Test Certificate")
		report = self._submitted_report()
		cert = issue_service_certificate(report.name, "Hydro Test Certificate", self.equipment_a.name, frappe.generate_hash())
		revoked = revoke_service_certificate(cert.name, "Superseded after retest")
		self.assertEqual(revoked.status, "Revoked")
		self.assertEqual(get_service_certificate(cert.name).revocation_reason, "Superseded after retest")

	def test_scope_direct_create_and_document_projection(self):
		frappe.set_user(self.technician_user_b)
		with self.assertRaises(frappe.PermissionError):
			generate_service_report(self.job_a, generation_key=frappe.generate_hash())
		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": "Service Report", "service_job": self.job_a}).insert()
		doc = generate_service_report(self.job_a, generation_key=frappe.generate_hash())
		documents = list_service_documents(self.job_a)
		self.assertIn(doc.name, [row.name for row in documents["reports"]])
