from __future__ import annotations

import frappe

from fsm.failure_analysis import (
	apply_priority_suggestion,
	create_failure_analysis,
	get_failure_analysis,
	list_failure_analyses,
	transition_failure_analysis,
	update_failure_analysis,
)
from fsm.tests.test_fire_safety import FireSafetyFixture


class TestFailureAnalysis(FireSafetyFixture):
	def _create(self, **values):
		payload = {
			"failure_code": "PRESSURE-LOSS",
			"symptom": "Pressure falls below the operating range",
			"severity": "Major",
		}
		payload.update(values)
		return create_failure_analysis(self.job_a, self.equipment_a.name, **payload)

	def test_command_owned_lifecycle_and_required_evidence(self):
		frappe.set_user(self.technician_user_a)
		doc = self._create()
		self.assertEqual(doc.status, "Draft")
		transition_failure_analysis(doc.name, "Inspection")
		transition_failure_analysis(doc.name, "Analysis")
		with self.assertRaises(frappe.ValidationError):
			transition_failure_analysis(doc.name, "Root Cause Identified")
		update_failure_analysis(doc.name, root_cause="Valve seat leakage")
		transition_failure_analysis(doc.name, "Root Cause Identified")
		update_failure_analysis(doc.name, corrective_action="Replace valve assembly")
		transition_failure_analysis(doc.name, "Corrective Action")
		transition_failure_analysis(doc.name, "Verification")
		with self.assertRaises(frappe.ValidationError):
			transition_failure_analysis(doc.name, "Closed")
		update_failure_analysis(doc.name, verification="Held pressure for 30 minutes")
		closed = transition_failure_analysis(doc.name, "Closed")
		self.assertEqual(closed.status, "Closed")
		with self.assertRaises(frappe.ValidationError):
			update_failure_analysis(doc.name, symptom="changed")

	def test_repeat_window_escalates_and_suggests_priority(self):
		frappe.db.set_single_value("Service Settings", "repeat_failure_window_days", 30)
		frappe.db.set_single_value("Service Settings", "repeat_failure_escalation_count", 1)
		frappe.set_user(self.technician_user_a)
		first = self._create(severity="Minor")
		second = self._create(severity="Minor", failure_code="PRESSURE-LOSS-2")
		self.assertEqual(first.repeat_count, 0)
		self.assertEqual(second.repeat_count, 1)
		self.assertEqual(second.repeat_failure, 1)
		self.assertEqual(second.escalated, 1)
		self.assertEqual(second.priority_suggestion, "Urgent")

	def test_safety_risk_is_escalated_immediately(self):
		frappe.set_user(self.technician_user_a)
		doc = self._create(safety_risk=1, severity="Observation")
		self.assertEqual(doc.escalated, 1)
		self.assertEqual(doc.priority_suggestion, "Urgent")

	def test_job_priority_never_changes_silently(self):
		frappe.set_user(self.technician_user_a)
		doc = self._create(severity="Critical")
		original = frappe.db.get_value("Service Job", self.job_a, "priority")
		self.assertNotEqual(original, "Urgent")
		with self.assertRaises(frappe.PermissionError):
			apply_priority_suggestion(doc.name)
		frappe.set_user(self.manager_a)
		result = apply_priority_suggestion(doc.name)
		self.assertTrue(result["changed"])
		self.assertEqual(frappe.db.get_value("Service Job", self.job_a, "priority"), "Urgent")
		self.assertTrue(
			frappe.db.exists(
				"Service Event Log",
				{"service_job": self.job_a, "event_type": "JobPriorityChangedFromFailureAnalysis"},
			)
		)

	def test_direct_create_and_state_forgery_are_blocked(self):
		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Failure Analysis",
					"service_job": self.job_a,
					"installed_equipment": self.equipment_a.name,
					"failure_code": "FORGED",
					"symptom": "forged",
				}
			).insert()
		doc = self._create()
		record = frappe.get_doc("Failure Analysis", doc.name)
		record.status = "Closed"
		with self.assertRaises(frappe.PermissionError):
			record.save()

	def test_actor_and_context_scope(self):
		frappe.set_user(self.technician_user_b)
		with self.assertRaises(frappe.PermissionError):
			self._create()
		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.ValidationError):
			self._create(service_visit="missing-visit")

	def test_scoped_list_get_and_correlated_event(self):
		frappe.set_user(self.technician_user_a)
		doc = self._create()
		self.assertEqual(get_failure_analysis(doc.name).name, doc.name)
		self.assertEqual([row.name for row in list_failure_analyses(service_job=self.job_a)], [doc.name])
		self.assertTrue(
			frappe.db.exists(
				"Service Event Log",
				{
					"service_job": self.job_a,
					"installed_equipment": self.equipment_a.name,
					"event_type": "FailureAnalysisCreated",
				},
			)
		)
