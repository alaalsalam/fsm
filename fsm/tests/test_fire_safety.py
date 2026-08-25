from __future__ import annotations

import frappe
from frappe.utils import add_months, getdate

from fsm.fire_safety.commands import (
	install_standard_extinguisher_template,
	record_extinguisher_service,
	update_fire_safety_profile,
)
from fsm.tests.test_installed_base import _item, _manual_equipment, _site
from fsm.tests.test_security import SecurityFixture


class FireSafetyFixture(SecurityFixture):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.site_a = _site(self.customer_a, company=self.company_a, label="Fire A")
		self.equipment_a = _manual_equipment(self.customer_a, _item(), self.site_a.name, self.company_a)
		job = frappe.get_doc("Service Job", self.job_a)
		job.append("equipment", {"installed_equipment": self.equipment_a.name, "service_scope": "Inspect"})
		job.flags.fsm_command = True
		job.save()

	def profile(self, **values):
		profile = {
			"equipment_category": "Fire Extinguisher",
			"extinguisher_type": "Dry Chemical Powder",
			"capacity": 6,
			"capacity_uom": "Kg",
			"agent_type": "ABC Powder",
			"fire_manufacturer": "Safety Co",
			"fire_model": "ABC-6",
			"manufacturing_date": "2024-01-15",
			"expiry_date": "2034-01-15",
			"pressure_rating": 15,
			"hydro_test_interval_months": 60,
		}
		profile.update(values)
		return update_fire_safety_profile(self.equipment_a.name, **profile)


class TestFireExtinguisherProfile(FireSafetyFixture):
	def test_profile_uses_installed_equipment_and_calculates_hydro_due(self):
		profile = self.profile()
		self.assertEqual(profile.equipment_category, "Fire Extinguisher")
		self.assertEqual(profile.item_code, self.equipment_a.item_code)
		self.assertEqual(profile.hydro_due_date, getdate(add_months("2024-01-15", 60)))

	def test_profile_validates_dates_and_interval(self):
		with self.assertRaises(frappe.ValidationError):
			self.profile(manufacturing_date="2035-01-01")
		with self.assertRaises(frappe.ValidationError):
			self.profile(hydro_test_interval_months=0)

	def test_standard_template_is_complete_configurable_and_idempotent(self):
		first = install_standard_extinguisher_template(self.company_a)
		second = install_standard_extinguisher_template(self.company_a)
		self.assertEqual(first.name, second.name)
		self.assertEqual(first.status, "Active")
		codes = {row.code for row in first["items"]}
		self.assertEqual(
			codes,
			{
				"BODY",
				"CORROSION",
				"PRESSURE",
				"HOSE",
				"NOZZLE",
				"VALVE",
				"PIN",
				"SEAL",
				"LABEL",
				"MOUNTING",
				"ACCESS",
				"SIGNAGE",
				"WEIGHT",
				"MFG_DATE",
				"EXPIRY",
				"LAST_REFILL",
				"HYDRO",
				"PHOTOS",
				"NOTES",
			},
		)

	def test_refill_and_hydro_history_is_job_scoped_without_stock_side_effects(self):
		self.profile()
		before = frappe.db.count("Stock Entry")
		frappe.set_user(self.technician_user_a)
		result = record_extinguisher_service(
			self.job_a,
			self.equipment_a.name,
			refill_date="2026-08-25",
			refill_result="Completed",
			hydro_test_date="2026-08-20",
		)
		self.assertEqual(result.last_refill_result, "Completed")
		self.assertEqual(result.hydro_due_date, getdate(add_months("2026-08-20", 60)))
		self.assertEqual(frappe.db.count("Stock Entry"), before)
		self.assertTrue(
			frappe.db.exists(
				"Service Event Log",
				{
					"installed_equipment": self.equipment_a.name,
					"event_type": "FireExtinguisherServiceRecorded",
				},
			)
		)

	def test_non_extinguisher_and_unrelated_actor_are_blocked(self):
		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.ValidationError):
			record_extinguisher_service(self.job_a, self.equipment_a.name, refill_date="2026-08-25")
		frappe.set_user("Administrator")
		self.profile()
		frappe.set_user(self.technician_user_b)
		with self.assertRaises(frappe.PermissionError):
			record_extinguisher_service(self.job_a, self.equipment_a.name, refill_date="2026-08-25")

	def test_cross_company_profile_and_template_are_blocked(self):
		frappe.set_user(self.manager_b)
		with self.assertRaises(frappe.PermissionError):
			self.profile()
		with self.assertRaises(frappe.PermissionError):
			install_standard_extinguisher_template(self.company_a)
