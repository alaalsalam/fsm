import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from fsm.api import _default_customer_group, _default_territory
from fsm.process.guided import schedule_job_with_visit
from fsm.service_operations.api import get_service_request, list_service_requests
from fsm.service_operations.commands import (
	cancel_job,
	cancel_request,
	cancel_visit,
	check_in_visit,
	check_out_visit,
	complete_job,
	complete_visit,
	create_job_from_request,
	create_visit,
	dispatch_job,
	dispatch_visit,
	hold_job,
	open_request,
	plan_job,
	resume_job,
	schedule_job,
	start_job,
	start_travel,
	start_visit_work,
	triage_request,
)
from fsm.tests.test_security import SecurityFixture


class TestCanonicalServiceOperations(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.customer = (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": f"CORE {frappe.generate_hash(length=8)}",
					"customer_type": "Individual",
					"customer_group": _default_customer_group(),
					"territory": _default_territory(),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.technician = (
			frappe.get_doc(
				{
					"doctype": "Technician",
					"technician_name": f"CORE Tech {frappe.generate_hash(length=8)}",
					"user": "Administrator",
					"company": self.company,
					"active": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		request = frappe.get_doc(
			{
				"doctype": "Service Request",
				"company": self.company,
				"customer": self.customer,
				"subject": "Canonical request",
				"status": "Open",
				"source": "Manual",
			}
		)
		request.flags.fsm_command = True
		self.request = request.insert(ignore_permissions=True).name

	def _job(self):
		return create_job_from_request(self.request, "initial", "Console").name

	def _scheduled_job(self):
		job = self._job()
		plan_job(job)
		schedule_job(job, now_datetime(), add_to_date(now_datetime(), hours=2))
		return job

	def test_request_conversion_is_one_to_many_and_idempotent(self):
		triage_request(self.request)
		first = create_job_from_request(self.request, "retry-key")
		retry = create_job_from_request(self.request, "retry-key")
		second = create_job_from_request(self.request, "second-job")
		self.assertEqual(first.name, retry.name)
		self.assertNotEqual(first.name, second.name)
		self.assertEqual(frappe.db.count("Service Job", {"service_request": self.request}), 2)
		self.assertEqual(frappe.db.get_value("Service Request", self.request, "status"), "Converted")

	def test_job_and_visit_happy_path_with_projection(self):
		job = self._scheduled_job()
		visit = create_visit(job, now_datetime(), primary_technician=self.technician).name
		dispatch_job(job, self.technician)
		dispatch_visit(visit)
		start_travel(visit)
		self.assertEqual(frappe.db.get_value("Service Job", job, "phase"), "Travel")
		check_in_visit(visit, 24.7136, 46.6753, 8)
		start_visit_work(visit)
		self.assertEqual(frappe.db.get_value("Service Job", job, "status"), "In Progress")
		check_out_visit(visit, 24.7137, 46.6754, 9)
		complete_visit(visit)
		self.assertEqual(complete_job(job).status, "Completed")
		self.assertGreaterEqual(frappe.db.count("Service Event Log", {"service_job": job}), 10)

	def test_guided_scheduling_is_retry_safe(self):
		job = self._job()
		start = now_datetime()
		end = add_to_date(start, hours=2)
		first = schedule_job_with_visit(job, start, end, primary_technician=self.technician)
		retry = schedule_job_with_visit(job, start, end, primary_technician=self.technician)
		self.assertTrue(first["visit_created"])
		self.assertFalse(retry["visit_created"])
		self.assertEqual(first["visit"], retry["visit"])
		self.assertEqual(frappe.db.count("Service Visit", {"service_job": job}), 1)

	def test_hold_resume_cancel_and_illegal_transition(self):
		job = self._scheduled_job()
		hold_job(job, "Material")
		self.assertEqual(resume_job(job).status, "Scheduled")
		cancel_job(job)
		with self.assertRaises(frappe.ValidationError):
			plan_job(job)

	def test_active_visit_blocks_completion(self):
		job = self._scheduled_job()
		dispatch_job(job, self.technician)
		visit = create_visit(job, primary_technician=self.technician).name
		dispatch_visit(visit)
		start_travel(visit)
		check_in_visit(visit)
		start_visit_work(visit)
		with self.assertRaises(frappe.ValidationError):
			complete_job(job)

	def test_generic_status_write_and_direct_event_create_are_blocked(self):
		job = self._job()
		doc = frappe.get_doc("Service Job", job)
		doc.status = "Completed"
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Service Event Log",
					"event_id": frappe.generate_hash(),
					"event_type": "forged",
					"reference_doctype": "Service Job",
					"reference_name": job,
					"event_time": now_datetime(),
					"source": "API",
				}
			).insert(ignore_permissions=True)

	def test_checklist_does_not_complete_job(self):
		job = self._scheduled_job()
		doc = frappe.get_doc("Service Job", job)
		doc.append("tasks", {"task": "Required", "status": "Done", "completed": 1})
		doc.save()
		self.assertEqual(frappe.db.get_value("Service Job", job, "status"), "Scheduled")

	def test_request_commands_and_illegal_transitions(self):
		draft = frappe.get_doc(
			{
				"doctype": "Service Request",
				"company": self.company,
				"customer": self.customer,
				"subject": "Draft request",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(draft.status, "Draft")
		self.assertEqual(open_request(draft.name).status, "Open")
		self.assertEqual(triage_request(draft.name).status, "Triaged")
		self.assertEqual(cancel_request(draft.name).status, "Cancelled")
		with self.assertRaises(frappe.ValidationError):
			open_request(draft.name)
		forged = frappe.get_doc(
			{
				"doctype": "Service Request",
				"company": self.company,
				"customer": self.customer,
				"subject": "Forged state",
				"status": "Converted",
			}
		)
		with self.assertRaises(frappe.PermissionError):
			forged.insert(ignore_permissions=True)

	def test_explicit_job_transitions_and_completion(self):
		job = self._scheduled_job()
		dispatch_job(job, self.technician)
		self.assertEqual(start_job(job).status, "In Progress")
		self.assertEqual(hold_job(job, "Customer").status, "On Hold")
		self.assertEqual(resume_job(job).status, "In Progress")
		self.assertEqual(complete_job(job).status, "Completed")
		with self.assertRaises(frappe.ValidationError):
			start_job(job)

	def test_visit_cancel_invalid_transition_and_multiple_visits(self):
		job = self._scheduled_job()
		first = create_visit(job, primary_technician=self.technician).name
		second = create_visit(job, primary_technician=self.technician).name
		self.assertEqual(frappe.db.count("Service Visit", {"service_job": job}), 2)
		self.assertEqual(cancel_visit(first).status, "Cancelled")
		with self.assertRaises(frappe.ValidationError):
			dispatch_visit(first)
		dispatch_job(job, self.technician)
		dispatch_visit(second)
		start_travel(second)
		with self.assertRaises(frappe.ValidationError):
			check_in_visit(second, 91, 181, 5)

	def test_completed_visit_does_not_complete_job_or_hide_open_visit(self):
		job = self._scheduled_job()
		first = create_visit(job, primary_technician=self.technician).name
		second = create_visit(job, primary_technician=self.technician).name
		dispatch_job(job, self.technician)
		for command in (
			dispatch_visit,
			start_travel,
			check_in_visit,
			start_visit_work,
			check_out_visit,
			complete_visit,
		):
			command(first)
		self.assertEqual(frappe.db.get_value("Service Job", job, "status"), "In Progress")
		self.assertEqual(frappe.db.get_value("Service Visit", second, "status"), "Planned")
		with self.assertRaises(frappe.ValidationError):
			complete_job(job)

	def test_event_transition_values_actor_and_immutability(self):
		job = self._job()
		plan_job(job, correlation_id="core-correlation")
		event = frappe.get_last_doc("Service Event Log", filters={"service_job": job})
		self.assertEqual((event.from_status, event.to_status), ("Draft", "Planned"))
		self.assertEqual(event.actor, "Administrator")
		self.assertEqual(event.correlation_id, "core-correlation")
		event.to_status = "Forged"
		with self.assertRaises(frappe.PermissionError):
			event.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Service Event Log", event.name, ignore_permissions=True)

	def test_direct_visit_create_is_blocked(self):
		job = self._scheduled_job()
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc({"doctype": "Service Visit", "service_job": job, "visit_number": 1}).insert(
				ignore_permissions=True
			)


class TestCoreAuthorization(SecurityFixture):
	def test_customer_manager_technician_and_guest_boundaries(self):
		frappe.set_user("Administrator")
		visit_b = create_visit(self.job_b, primary_technician=self.technician_b).name
		dispatch_visit(visit_b)

		frappe.set_user(self.customer_user_a)
		self.assertEqual(get_service_request(self.request_a).name, self.request_a)
		with self.assertRaises(frappe.PermissionError):
			get_service_request(self.request_b)

		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.PermissionError):
			start_travel(visit_b)

		frappe.set_user(self.manager_a)
		with self.assertRaises(frappe.PermissionError):
			create_job_from_request(self.request_b, "cross-company")

		frappe.set_user("Guest")
		with self.assertRaises(frappe.AuthenticationError):
			list_service_requests()
