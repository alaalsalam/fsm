from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from fsm.maintenance.api import get_plan, list_occurrences, list_plans
from fsm.maintenance.commands import (
	create_plan,
	generate_plan_occurrences,
	release_plan_occurrences,
	reschedule_plan_occurrence,
	skip_plan_occurrence,
	transition_plan,
	update_plan,
)
from fsm.maintenance.engine import update_occurrence_statuses
from fsm.maintenance.tasks import run_daily_maintenance
from fsm.service_operations.commands import complete_job, schedule_job, start_job
from fsm.tests.test_installed_base import _customer, _item, _manual_equipment, _site
from fsm.tests.test_security import SecurityFixture


def _make_plan(
	company: str,
	customer: str,
	site: str,
	equipment: list[str],
	*,
	start_date=None,
	interval_count=1,
	interval_unit="Months",
	lead_days=7,
	grace_days=0,
	catch_up_policy="Generate Missed",
	timezone="Asia/Riyadh",
):
	return create_plan(
		plan_title=f"PM {frappe.generate_hash(length=8)}",
		company=company,
		customer=customer,
		customer_site=site,
		start_date=start_date or nowdate(),
		timezone=timezone,
		forecast_horizon_days=100,
		due_window_days=7,
		catch_up_policy=catch_up_policy,
		dst_policy="Next Valid Time",
		equipment=[{"installed_equipment": name, "active": 1} for name in equipment],
		lines=[
			{
				"line_code": "PM-STD",
				"service_type": "Preventive Maintenance",
				"interval_count": interval_count,
				"interval_unit": interval_unit,
				"first_due_date": start_date or nowdate(),
				"scheduled_time": "09:00:00",
				"equipment_scope": "All Plan Equipment",
				"lead_days": lead_days,
				"grace_days": grace_days,
				"auto_release_job": 1,
				"active": 1,
			}
		],
	)


class PreventiveMaintenanceFixture(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.customer = _customer("PM Customer")
		self.item = _item(warranty_days=0)
		self.site = _site(self.customer, company=self.company, label="PM")
		self.equipment = _manual_equipment(self.customer, self.item, self.site.name, self.company)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()


class TestMaintenancePlanModel(PreventiveMaintenanceFixture):
	def test_plan_validates_site_and_equipment_ownership(self):
		other_customer = _customer("PM Other")
		other_site = _site(other_customer, company=self.company, label="PM Other")
		with self.assertRaises(frappe.ValidationError):
			_make_plan(self.company, self.customer, other_site.name, [self.equipment.name])

	def test_plan_lifecycle_is_command_owned(self):
		plan = _make_plan(self.company, self.customer, self.site.name, [self.equipment.name])
		active = transition_plan(plan.name, "Active")
		self.assertEqual(active.status, "Active")
		self.assertEqual(active.active, 1)
		doc = frappe.get_doc("Maintenance Plan", plan.name)
		doc.status = "Paused"
		with self.assertRaises(frappe.PermissionError):
			doc.save()
		self.assertEqual(transition_plan(plan.name, "Paused").status, "Paused")

	def test_invalid_interval_and_timezone_are_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			_make_plan(
				self.company,
				self.customer,
				self.site.name,
				[self.equipment.name],
				interval_count=0,
			)
		with self.assertRaises(frappe.ValidationError):
			_make_plan(
				self.company,
				self.customer,
				self.site.name,
				[self.equipment.name],
				timezone="Not/A-Timezone",
			)


class TestMaintenanceOccurrenceEngine(PreventiveMaintenanceFixture):
	def test_generation_is_idempotent_and_retains_timezone_audit(self):
		plan = _make_plan(self.company, self.customer, self.site.name, [self.equipment.name])
		transition_plan(plan.name, "Active")
		first = generate_plan_occurrences(plan.name)["occurrences"]
		second = generate_plan_occurrences(plan.name)["occurrences"]
		self.assertEqual(first, second)
		self.assertEqual(
			frappe.db.count("Maintenance Occurrence", {"maintenance_plan": plan.name}), len(set(first))
		)
		row = frappe.get_doc("Maintenance Occurrence", first[0])
		self.assertEqual(row.due_timezone, "Asia/Riyadh")
		self.assertEqual(row.due_offset_minutes, 180)

	def test_days_weeks_months_and_years_are_supported(self):
		for unit in ("Days", "Weeks", "Months", "Years"):
			plan = _make_plan(
				self.company,
				self.customer,
				self.site.name,
				[self.equipment.name],
				interval_unit=unit,
			)
			transition_plan(plan.name, "Active")
			self.assertTrue(frappe.db.exists("Maintenance Occurrence", {"maintenance_plan": plan.name}))

	def test_skip_missed_policy_and_overdue_projection(self):
		start = add_days(nowdate(), -10)
		plan = _make_plan(
			self.company,
			self.customer,
			self.site.name,
			[self.equipment.name],
			start_date=start,
			interval_count=30,
			interval_unit="Days",
			catch_up_policy="Skip Missed",
		)
		transition_plan(plan.name, "Active")
		self.assertEqual(
			frappe.db.get_value(
				"Maintenance Occurrence", {"maintenance_plan": plan.name, "due_date": start}, "status"
			),
			"Skipped",
		)
		other = _make_plan(
			self.company,
			self.customer,
			self.site.name,
			[self.equipment.name],
			start_date=start,
			interval_count=30,
			interval_unit="Days",
			grace_days=1,
		)
		transition_plan(other.name, "Active")
		update_occurrence_statuses()
		self.assertEqual(
			frappe.db.get_value(
				"Maintenance Occurrence", {"maintenance_plan": other.name, "due_date": start}, "status"
			),
			"Overdue",
		)

	def test_skip_and_reschedule_keep_durable_history(self):
		plan = _make_plan(self.company, self.customer, self.site.name, [self.equipment.name])
		transition_plan(plan.name, "Active")
		rows = list_occurrences(maintenance_plan=plan.name)
		first, second = rows[0], rows[1]
		skipped = skip_plan_occurrence(first.name, "Customer unavailable")
		self.assertEqual(skipped.status, "Skipped")
		rescheduled = reschedule_plan_occurrence(second.name, add_days(second.due_date, 5))
		self.assertEqual(rescheduled.rescheduled_from, second.name)
		self.assertEqual(frappe.db.get_value("Maintenance Occurrence", second.name, "status"), "Cancelled")

	def test_plan_revision_supersedes_open_occurrences(self):
		plan = _make_plan(self.company, self.customer, self.site.name, [self.equipment.name])
		transition_plan(plan.name, "Active")
		old_revision = plan.revision
		doc = frappe.get_doc("Maintenance Plan", plan.name)
		lines = [row.as_dict() for row in doc.lines]
		lines[0]["interval_count"] = 2
		updated = update_plan(plan.name, lines=lines)
		self.assertEqual(updated.revision, old_revision + 1)
		self.assertFalse(
			frappe.db.exists(
				"Maintenance Occurrence",
				{
					"maintenance_plan": plan.name,
					"plan_revision": old_revision,
					"status": ["in", ["Forecast", "Due", "Overdue"]],
				},
			)
		)

	def test_release_groups_many_equipment_into_one_job_and_retries(self):
		equipment = [self.equipment.name]
		for _ in range(5):
			equipment.append(_manual_equipment(self.customer, self.item, self.site.name, self.company).name)
		plan = _make_plan(self.company, self.customer, self.site.name, equipment)
		transition_plan(plan.name, "Active")
		first = release_plan_occurrences(maintenance_plan=plan.name)["jobs"]
		second = release_plan_occurrences(maintenance_plan=plan.name)["jobs"]
		self.assertEqual(len(first), 1)
		self.assertEqual(second, [])
		job = frappe.get_doc("Service Job", first[0])
		self.assertEqual(job.status, "Planned")
		self.assertEqual(len(job.equipment), 6)
		self.assertEqual(
			frappe.db.count("Service Job", {"maintenance_release_key": job.maintenance_release_key}), 1
		)

	def test_job_completion_projects_all_occurrences(self):
		plan = _make_plan(self.company, self.customer, self.site.name, [self.equipment.name])
		transition_plan(plan.name, "Active")
		job = release_plan_occurrences(maintenance_plan=plan.name)["jobs"][0]
		schedule_job(job, f"{nowdate()} 09:00:00")
		start_job(job)
		complete_job(job)
		self.assertFalse(
			frappe.db.exists("Maintenance Occurrence", {"released_job": job, "status": "Released"})
		)
		self.assertTrue(
			frappe.db.exists("Maintenance Occurrence", {"released_job": job, "status": "Completed"})
		)

	def test_daily_scheduler_is_retry_safe(self):
		plan = _make_plan(self.company, self.customer, self.site.name, [self.equipment.name])
		transition_plan(plan.name, "Active")
		run_daily_maintenance()
		before = frappe.db.count("Maintenance Occurrence", {"maintenance_plan": plan.name})
		run_daily_maintenance()
		self.assertEqual(frappe.db.count("Maintenance Occurrence", {"maintenance_plan": plan.name}), before)
		self.assertEqual(frappe.db.count("Service Job", {"customer": self.customer}), 1)


class TestPreventiveMaintenanceAuthorization(SecurityFixture):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		item = _item(warranty_days=0)
		self.site_a = _site(self.customer_a, company=self.company_a, label="PM Security A")
		self.equipment_a = _manual_equipment(self.customer_a, item, self.site_a.name, self.company_a)
		self.plan_a = _make_plan(self.company_a, self.customer_a, self.site_a.name, [self.equipment_a.name])

	def test_manager_and_customer_scope(self):
		frappe.set_user(self.manager_a)
		self.assertIn(self.plan_a.name, {row.name for row in list_plans()})
		frappe.set_user(self.manager_b)
		with self.assertRaises(frappe.PermissionError):
			transition_plan(self.plan_a.name, "Active")
		frappe.set_user(self.customer_user_a)
		self.assertEqual(get_plan(self.plan_a.name).name, self.plan_a.name)

	def test_customer_cannot_generate_or_release(self):
		frappe.set_user("Administrator")
		transition_plan(self.plan_a.name, "Active")
		frappe.set_user(self.customer_user_a)
		with self.assertRaises(frappe.PermissionError):
			generate_plan_occurrences(self.plan_a.name)
		with self.assertRaises(frappe.PermissionError):
			release_plan_occurrences(maintenance_plan=self.plan_a.name)
