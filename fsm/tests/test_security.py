from unittest.mock import patch

import frappe
from frappe.contacts.doctype.contact.contact import Contact
from frappe.tests.utils import FrappeTestCase

from fsm.api import (
	_default_customer_group,
	_default_territory,
	complete_job,
	get_dashboard_stats,
	get_dispatch_jobs,
	get_my_appointments,
	get_my_job,
	get_my_jobs,
	get_portal_session,
	register_customer,
)
from fsm.feedback import get_feedback, submit_feedback
from fsm.messaging import get_messages, post_message
from fsm.security.policy import require_job_access


class SecurityFixture(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company_a = "_Test Company"
		self.company_b = "_Test Company 1"
		self._remove_stale_fixtures()
		self.customer_a = self._make_customer("GATE Customer A")
		self.customer_b = self._make_customer("GATE Customer B")
		self.manager_a = self._make_user("gate.manager.a@example.com", "FSM Manager")
		self.manager_b = self._make_user("gate.manager.b@example.com", "FSM Manager")
		self.technician_user_a = self._make_user("gate.tech.a@example.com", "FSM Technician")
		self.technician_user_b = self._make_user("gate.tech.b@example.com", "FSM Technician")
		self.customer_user_a = self._make_user(
			"gate.customer.a@example.com", "FSM Customer", user_type="Website User"
		)
		self.customer_user_b = self._make_user(
			"gate.customer.b@example.com", "FSM Customer", user_type="Website User"
		)
		self._allow_company(self.manager_a, self.company_a)
		self._allow_company(self.manager_b, self.company_b)
		self._link_customer(self.customer_user_a, self.customer_a)
		self._link_customer(self.customer_user_b, self.customer_b)
		self.technician_a = self._make_technician("GATE Technician A", self.technician_user_a, self.company_a)
		self.technician_b = self._make_technician("GATE Technician B", self.technician_user_b, self.company_b)
		self.job_a = self._make_job(self.company_a, self.customer_a, self.technician_a)
		self.job_b = self._make_job(self.company_b, self.customer_b, self.technician_b)
		self.appointment_a = self._make_appointment(self.company_a, self.customer_a)
		self.appointment_b = self._make_appointment(self.company_b, self.customer_b)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _remove_stale_fixtures(self):
		"""Keep this suite repeatable after an interrupted or failed test run."""
		customers = ["GATE Customer A", "GATE Customer B"]
		jobs = frappe.get_all("Service Job", filters={"customer": ["in", customers]}, pluck="name")
		for doctype in (
			"Service Job Message",
			"Service Feedback",
			"Service Time Log",
			"Customer Field Note",
			"Technician Location Log",
			"Service Return",
		):
			frappe.db.delete(doctype, {"service_job": ["in", jobs]})
		frappe.db.delete("Service Appointment", {"customer_name": ["in", customers]})
		frappe.db.delete("Service Job", {"name": ["in", jobs]})

	def _make_user(self, email: str, role: str, user_type: str = "System User") -> str:
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True)
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"user_type": user_type,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
		return user.name

	def _make_customer(self, name: str) -> str:
		if frappe.db.exists("Customer", name):
			frappe.delete_doc("Customer", name, force=True)
		return (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_type": "Individual",
					"customer_group": _default_customer_group(),
					"territory": _default_territory(),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _allow_company(self, user: str, company: str):
		frappe.get_doc(
			{"doctype": "User Permission", "user": user, "allow": "Company", "for_value": company}
		).insert(ignore_permissions=True)

	def _link_customer(self, user: str, customer: str):
		contact = frappe.get_doc({"doctype": "Contact", "first_name": customer, "user": user})
		contact.append("email_ids", {"email_id": user, "is_primary": 1})
		contact.append("links", {"link_doctype": "Customer", "link_name": customer})
		contact.insert(ignore_permissions=True)

	def _make_technician(self, name: str, user: str, company: str) -> str:
		if frappe.db.exists("Technician", name):
			frappe.delete_doc("Technician", name, force=True)
		return (
			frappe.get_doc(
				{
					"doctype": "Technician",
					"technician_name": name,
					"user": user,
					"company": company,
					"active": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _make_job(self, company: str, customer: str, technician: str) -> str:
		return (
			frappe.get_doc(
				{
					"doctype": "Service Job",
					"company": company,
					"customer": customer,
					"primary_technician": technician,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _make_appointment(self, company: str, customer: str) -> str:
		return (
			frappe.get_doc(
				{
					"doctype": "Service Appointment",
					"company": company,
					"customer": customer,
					"customer_name": customer,
					"contact_phone": "+49123456789",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)


class TestDataIsolation(SecurityFixture):
	def test_technician_can_only_read_and_mutate_assigned_job(self):
		frappe.set_user(self.technician_user_a)
		self.assertEqual([row.name for row in get_dispatch_jobs()], [self.job_a])
		with self.assertRaises(frappe.PermissionError):
			complete_job(self.job_b)
		self.assertEqual(complete_job(self.job_a).status, "Completed")

	def test_customer_can_only_read_owned_records(self):
		frappe.set_user(self.customer_user_a)
		self.assertEqual([row.name for row in get_my_jobs()], [self.job_a])
		self.assertEqual([row.name for row in get_my_appointments()], [self.appointment_a])
		self.assertEqual(get_my_job(self.job_a)["name"], self.job_a)
		self.assertTrue(post_message(self.job_a, "customer-owned message")["name"])
		self.assertTrue(submit_feedback(self.job_a, 5, "customer-owned feedback")["name"])
		self.assertEqual(get_feedback(self.job_a).rating, 5)
		with self.assertRaises(frappe.PermissionError):
			get_my_job(self.job_b)
		with self.assertRaises(frappe.PermissionError):
			get_messages(self.job_b)

	def test_manager_cannot_cross_company_scope(self):
		frappe.set_user(self.manager_a)
		self.assertEqual([row.name for row in get_dispatch_jobs()], [self.job_a])
		with self.assertRaises(frappe.PermissionError):
			require_job_access(self.job_b)

	def test_dashboard_respects_company_scope(self):
		frappe.set_user(self.manager_a)
		stats = get_dashboard_stats()
		self.assertEqual(stats["open_jobs"], 1)
		self.assertEqual(stats["completed_today"], 0)

	def test_guest_endpoints_are_explicit(self):
		frappe.set_user("Guest")
		self.assertEqual(get_portal_session(), {"authenticated": False})
		with self.assertRaises(frappe.AuthenticationError):
			get_dispatch_jobs()

	def test_child_document_cannot_bypass_root_permission(self):
		frappe.set_user(self.technician_user_b)
		message = frappe.get_doc(
			{
				"doctype": "Service Job Message",
				"service_job": self.job_a,
				"author_role": "Technician",
				"message": "cross-scope attempt",
			}
		)
		with self.assertRaises(frappe.PermissionError):
			message.insert()


class TestCustomerRegistration(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Website Settings", "disable_signup", 0)
		self.suffix = frappe.generate_hash(length=8).lower()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_missing_fields(self):
		with self.assertRaises(frappe.ValidationError):
			register_customer("", "", "")

	def test_existing_user(self):
		email = f"existing.{self.suffix}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Existing",
				"enabled": 1,
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			register_customer("Existing User", email, "GateTest!Pass123")

	def test_successful_registration_and_duplicate_retry(self):
		email = f"success.{self.suffix}@example.com"
		result = register_customer("Gate Customer", email, "GateTest!Pass123", "+49123456789")
		self.assertEqual(result["user"], email)
		self.assertTrue(frappe.db.exists("User", email))
		self.assertTrue(frappe.db.exists("Has Role", {"parent": email, "role": "FSM Customer"}))
		contact = frappe.db.get_value("Contact", {"user": email})
		self.assertTrue(contact)
		self.assertTrue(
			frappe.db.exists(
				"Dynamic Link",
				{
					"parent": contact,
					"parenttype": "Contact",
					"link_doctype": "Customer",
					"link_name": result["customer"],
				},
			)
		)
		with self.assertRaises(frappe.ValidationError):
			register_customer("Gate Customer", email, "GateTest!Pass123")

	def test_registration_rolls_back_on_contact_failure(self):
		email = f"rollback.{self.suffix}@example.com"
		with patch.object(Contact, "insert", side_effect=frappe.ValidationError("forced contact failure")):
			with self.assertRaises(frappe.ValidationError):
				register_customer("Rollback Customer", email, "GateTest!Pass123")
		self.assertFalse(frappe.db.exists("User", email))
		self.assertFalse(frappe.db.exists("Customer", "Rollback Customer"))
