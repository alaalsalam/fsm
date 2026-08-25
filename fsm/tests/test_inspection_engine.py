from __future__ import annotations

import frappe

from fsm.inspections.api import get_inspection, list_inspections, list_templates
from fsm.inspections.commands import (
	close_inspection_without_access,
	complete_inspection,
	create_template,
	save_inspection_responses,
	start_inspection,
	transition_template,
	update_template,
)
from fsm.tests.test_installed_base import _item, _manual_equipment, _site
from fsm.tests.test_security import SecurityFixture


def _template(company, items=None):
	doc = create_template(
		template_name=f"Inspection {frappe.generate_hash(length=8)}",
		company=company,
		items=items
		or [
			{
				"code": "BODY",
				"label": "Body condition",
				"response_type": "Pass/Fail",
				"required": 1,
				"evidence_required": 0,
				"failure_severity": "Major",
				"action_on_fail": "Repair",
			}
		],
	)
	return transition_template(doc.name, "Active")


class InspectionFixture(SecurityFixture):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.site_a = _site(self.customer_a, company=self.company_a, label="Inspection A")
		self.equipment_a = _manual_equipment(self.customer_a, _item(), self.site_a.name, self.company_a)
		job = frappe.get_doc("Service Job", self.job_a)
		job.append("equipment", {"installed_equipment": self.equipment_a.name, "service_scope": "Inspect"})
		job.flags.fsm_command = True
		job.save()
		self.template = _template(self.company_a)

	def start(self, template=None):
		return start_inspection(
			self.job_a,
			self.equipment_a.name,
			(template or self.template).name,
			technician=self.technician_a,
		)


class TestInspectionTemplate(InspectionFixture):
	def test_template_lifecycle_revision_and_immutability(self):
		doc = frappe.get_doc("Inspection Template", self.template.name)
		doc.status = "Inactive"
		with self.assertRaises(frappe.PermissionError):
			doc.save()
		old_revision = self.template.revision
		items = [row.as_dict() for row in doc.items]
		items[0]["label"] = "Revised body condition"
		updated = update_template(doc.name, items=items)
		self.assertEqual(updated.revision, old_revision + 1)

	def test_template_validates_codes_select_options_and_thresholds(self):
		with self.assertRaises(frappe.ValidationError):
			create_template(
				template_name="Duplicate codes",
				company=self.company_a,
				items=[
					{"code": "A", "label": "A", "response_type": "Text"},
					{"code": "A", "label": "B", "response_type": "Text"},
				],
			)
		with self.assertRaises(frappe.ValidationError):
			create_template(
				template_name="Bad select",
				company=self.company_a,
				items=[{"code": "S", "label": "S", "response_type": "Select"}],
			)
		with self.assertRaises(frappe.ValidationError):
			create_template(
				template_name="Bad range",
				company=self.company_a,
				items=[
					{
						"code": "P",
						"label": "Pressure",
						"response_type": "Measurement",
						"min_value": 10,
						"max_value": 5,
					}
				],
			)


class TestInspectionOutcomeEngine(InspectionFixture):
	def test_start_seeds_snapshot_and_multiple_inspections_are_allowed(self):
		first = self.start()
		second = self.start()
		self.assertNotEqual(first.name, second.name)
		self.assertEqual(first.template_revision, self.template.revision)
		self.assertEqual(first.results[0].item_code, "BODY")
		self.assertEqual(first.installed_equipment, self.equipment_a.name)

	def test_pass_fail_is_server_calculated(self):
		inspection = self.start()
		with self.assertRaises(frappe.ValidationError):
			save_inspection_responses(
				inspection.name,
				[{"item_code": "BODY", "response_value": "Fail", "passed": 1}],
			)
		doc = frappe.get_doc("Equipment Inspection", inspection.name)
		doc.results[0].passed = 1
		with self.assertRaises(frappe.PermissionError):
			doc.save()

	def test_pass_and_repair_outcomes(self):
		passed = self.start()
		save_inspection_responses(passed.name, [{"item_code": "BODY", "response_value": "Pass"}])
		self.assertEqual(complete_inspection(passed.name).overall_result, "Pass")
		failed = self.start()
		save_inspection_responses(failed.name, [{"item_code": "BODY", "response_value": "Fail"}])
		result = complete_inspection(failed.name)
		self.assertEqual(result.overall_result, "Needs Repair")
		self.assertEqual(result.corrective_action_hint, "Repair")

	def test_measurement_threshold_and_required_evidence(self):
		template = _template(
			self.company_a,
			[
				{
					"code": "PRESSURE",
					"label": "Pressure",
					"response_type": "Measurement",
					"required": 1,
					"min_value": 8,
					"max_value": 12,
					"measurement_unit": "bar",
					"evidence_required": 1,
					"failure_severity": "Critical",
					"action_on_fail": "Stop Work",
				}
			],
		)
		inspection = self.start(template)
		save_inspection_responses(inspection.name, [{"item_code": "PRESSURE", "numeric_value": 10}])
		with self.assertRaises(frappe.ValidationError):
			complete_inspection(inspection.name)
		save_inspection_responses(
			inspection.name,
			[{"item_code": "PRESSURE", "numeric_value": 7, "evidence": "/private/files/p.jpg"}],
		)
		self.assertEqual(complete_inspection(inspection.name).overall_result, "Fail")

	def test_yes_no_select_text_date_photo_and_signature(self):
		items = [
			{"code": "YN", "label": "Accessible", "response_type": "Yes/No", "required": 1},
			{
				"code": "SEL",
				"label": "Colour",
				"response_type": "Select",
				"required": 1,
				"options": "Red\nGreen",
			},
			{"code": "TXT", "label": "Notes", "response_type": "Text", "required": 1},
			{"code": "DATE", "label": "Date", "response_type": "Date", "required": 1},
			{"code": "PHOTO", "label": "Photo", "response_type": "Photo", "required": 1},
			{"code": "SIGN", "label": "Signature", "response_type": "Signature", "required": 1},
		]
		template = _template(self.company_a, items)
		inspection = self.start(template)
		save_inspection_responses(
			inspection.name,
			[
				{"item_code": "YN", "response_value": "Yes"},
				{"item_code": "SEL", "response_value": "Green"},
				{"item_code": "TXT", "response_value": "OK"},
				{"item_code": "DATE", "date_value": "2026-08-25"},
				{"item_code": "PHOTO", "attachment": "/private/files/photo.jpg"},
				{"item_code": "SIGN", "signature": "data:image/svg+xml;base64,PHN2Zy8+"},
			],
		)
		self.assertEqual(complete_inspection(inspection.name).overall_result, "Pass")

	def test_required_response_and_disposition_paths(self):
		inspection = self.start()
		with self.assertRaises(frappe.ValidationError):
			complete_inspection(inspection.name)
		skipped = close_inspection_without_access(inspection.name, "Skipped", "Customer declined")
		self.assertEqual(skipped.overall_result, "Skipped")
		with self.assertRaises(frappe.ValidationError):
			close_inspection_without_access(self.start().name, "Pass", "forced")


class TestInspectionAuthorization(InspectionFixture):
	def test_manager_template_and_job_scope(self):
		frappe.set_user(self.manager_a)
		self.assertIn(self.template.name, {row.name for row in list_templates()})
		self.assertEqual(self.start().service_job, self.job_a)
		frappe.set_user(self.manager_b)
		with self.assertRaises(frappe.PermissionError):
			self.start()

	def test_assigned_technician_can_execute_but_other_cannot(self):
		frappe.set_user(self.technician_user_a)
		inspection = start_inspection(self.job_a, self.equipment_a.name, self.template.name)
		save_inspection_responses(inspection.name, [{"item_code": "BODY", "response_value": "Pass"}])
		self.assertEqual(complete_inspection(inspection.name).overall_result, "Pass")
		frappe.set_user(self.technician_user_b)
		with self.assertRaises(frappe.PermissionError):
			get_inspection(inspection.name)

	def test_customer_read_only_scope(self):
		frappe.set_user("Administrator")
		inspection = self.start()
		save_inspection_responses(inspection.name, [{"item_code": "BODY", "response_value": "Pass"}])
		complete_inspection(inspection.name)
		frappe.set_user(self.customer_user_a)
		self.assertEqual(get_inspection(inspection.name).name, inspection.name)
		self.assertIn(inspection.name, {row.name for row in list_inspections()})
		with self.assertRaises(frappe.PermissionError):
			start_inspection(self.job_a, self.equipment_a.name, self.template.name)
