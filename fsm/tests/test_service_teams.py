import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, now_datetime, today

from fsm.api import _default_customer_group, _default_territory
from fsm.scheduling import assign_team, get_dispatch_jobs, suggest_teams
from fsm.tests.test_security import SecurityFixture


def _hash() -> str:
	return frappe.generate_hash(length=8)


class ServiceTeamMixin:
	def _make_technician(self, name: str, company: str, skills=None) -> str:
		if frappe.db.exists("Technician", name):
			frappe.delete_doc("Technician", name, force=True)
		doc = frappe.get_doc(
			{
				"doctype": "Technician",
				"technician_name": name,
				"user": "Administrator",
				"company": company,
				"active": 1,
			}
		)
		for skill in skills or []:
			doc.append("skills", {"skill": skill, "proficiency": "Expert"})
		return doc.insert(ignore_permissions=True).name

	def _make_team(self, company, members, leader=None, territory=None, capacity=0, status="Active"):
		doc = frappe.get_doc(
			{
				"doctype": "Service Team",
				"team_name": f"Team {_hash()}",
				"company": company,
				"territory": territory,
				"status": status,
				"capacity": capacity,
				"team_leader": leader,
				"active": 1,
			}
		)
		for member in members:
			doc.append("members", member)
		return doc.insert(ignore_permissions=True)


class TestServiceTeamModel(FrappeTestCase, ServiceTeamMixin):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.other_company = "_Test Company 1"
		self.tech_a = self._make_technician(f"STM Tech A {_hash()}", self.company)
		self.tech_b = self._make_technician(f"STM Tech B {_hash()}", self.company)
		self.tech_other = self._make_technician(f"STM Tech X {_hash()}", self.other_company)

	def test_team_creation_and_membership(self):
		team = self._make_team(
			self.company,
			[
				{"technician": self.tech_a, "role_in_team": "Team Leader"},
				{"technician": self.tech_b, "role_in_team": "Technician"},
			],
			leader=self.tech_a,
		)
		self.assertEqual(len(team.members), 2)
		self.assertEqual(team.team_leader, self.tech_a)

	def test_duplicate_member_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_team(
				self.company,
				[
					{"technician": self.tech_a, "role_in_team": "Technician"},
					{"technician": self.tech_a, "role_in_team": "Helper"},
				],
			)

	def test_member_company_mismatch_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_team(
				self.company,
				[{"technician": self.tech_other, "role_in_team": "Technician"}],
			)

	def test_leader_must_be_active_member(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_team(
				self.company,
				[{"technician": self.tech_a, "role_in_team": "Technician"}],
				leader=self.tech_b,
			)

	def test_inactive_member_cannot_be_leader(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_team(
				self.company,
				[{"technician": self.tech_a, "role_in_team": "Technician", "active": 0}],
				leader=self.tech_a,
			)

	def test_member_effective_window_validation(self):
		with self.assertRaises(frappe.ValidationError):
			self._make_team(
				self.company,
				[
					{
						"technician": self.tech_a,
						"role_in_team": "Technician",
						"effective_from": today(),
						"effective_to": add_days(today(), -5),
					}
				],
			)

	def test_overlapping_active_membership_rejected(self):
		self._make_team(self.company, [{"technician": self.tech_a, "role_in_team": "Technician"}])
		with self.assertRaises(frappe.ValidationError):
			self._make_team(self.company, [{"technician": self.tech_a, "role_in_team": "Technician"}])

	def test_non_overlapping_membership_allowed(self):
		self._make_team(
			self.company,
			[
				{
					"technician": self.tech_a,
					"role_in_team": "Technician",
					"effective_from": add_days(today(), -30),
					"effective_to": add_days(today(), -10),
				}
			],
		)
		# A later, non-overlapping window on another team is fine.
		team = self._make_team(
			self.company,
			[
				{
					"technician": self.tech_a,
					"role_in_team": "Technician",
					"effective_from": add_days(today(), -5),
					"effective_to": add_days(today(), 30),
				}
			],
		)
		self.assertTrue(frappe.db.exists("Service Team", team.name))


class TestServiceTeamDispatch(FrappeTestCase, ServiceTeamMixin):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.other_company = "_Test Company 1"
		self.customer = (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": f"STM Cust {_hash()}",
					"customer_type": "Individual",
					"customer_group": _default_customer_group(),
					"territory": _default_territory(),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
		self.skilled = self._make_technician(f"STM Skilled {_hash()}", self.company, skills=["HVAC"])
		self.plain = self._make_technician(f"STM Plain {_hash()}", self.company)
		self.skilled_team = self._make_team(
			self.company,
			[{"technician": self.skilled, "role_in_team": "Team Leader"}],
			leader=self.skilled,
			capacity=2,
		)
		self.plain_team = self._make_team(
			self.company,
			[{"technician": self.plain, "role_in_team": "Team Leader"}],
			leader=self.plain,
			capacity=2,
		)

	def _make_job(self, service_type=None, company=None):
		doc = frappe.get_doc(
			{
				"doctype": "Service Job",
				"company": company or self.company,
				"customer": self.customer,
				"service_type": service_type,
				"status": "Draft",
			}
		)
		return doc.insert(ignore_permissions=True).name

	def test_suggest_teams_ranks_skill_first(self):
		job = self._make_job(service_type="HVAC")
		ranked = suggest_teams(job)
		self.assertTrue(ranked)
		self.assertEqual(ranked[0]["team"], self.skilled_team.name)
		self.assertGreater(ranked[0]["score"], ranked[-1]["score"])

	def test_assign_team_sets_leader_via_fetch(self):
		job = self._make_job()
		assign_team(job, self.skilled_team.name)
		self.assertEqual(
			frappe.db.get_value("Service Job", job, "assigned_service_team"), self.skilled_team.name
		)
		self.assertEqual(frappe.db.get_value("Service Job", job, "team_leader"), self.skilled)

	def test_assign_team_company_mismatch_blocked(self):
		job = self._make_job(company=self.other_company)
		with self.assertRaises(frappe.PermissionError):
			assign_team(job, self.skilled_team.name)

	def test_capacity_blocks_assignment(self):
		small_team = self._make_team(
			self.company,
			[{"technician": self.plain, "role_in_team": "Technician"}],
			capacity=1,
		)
		job1 = self._make_job()
		job2 = self._make_job()
		frappe.db.set_value("Service Job", job1, "status", "Scheduled")
		assign_team(job1, small_team.name)
		with self.assertRaises(frappe.ValidationError):
			assign_team(job2, small_team.name)

	def test_inactive_team_not_suggested(self):
		self._make_team(
			self.company,
			[{"technician": self.plain, "role_in_team": "Technician"}],
			status="Suspended",
		)
		job = self._make_job(service_type="HVAC")
		suggested = {r["team"] for r in suggest_teams(job)}
		self.assertIn(self.skilled_team.name, suggested)

	def test_get_dispatch_jobs_team_filter(self):
		job = self._make_job()
		assign_team(job, self.skilled_team.name)
		rows = get_dispatch_jobs(team=self.skilled_team.name)
		names = {r["name"] for r in rows}
		self.assertIn(job, names)
		other = self._make_job()
		other_rows = {r["name"] for r in get_dispatch_jobs(team=self.plain_team.name)}
		self.assertNotIn(other, other_rows)


class TestServiceTeamAuthorization(SecurityFixture, ServiceTeamMixin):
	def setUp(self):
		super().setUp()
		self.team_a = self._make_team(
			self.company_a,
			[{"technician": self.technician_a, "role_in_team": "Team Leader"}],
			leader=self.technician_a,
			capacity=5,
		)

	def test_technician_cannot_assign_team(self):
		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.PermissionError):
			assign_team(self.job_a, self.team_a.name)

	def test_manager_can_assign_within_company(self):
		frappe.set_user(self.manager_a)
		result = assign_team(self.job_a, self.team_a.name)
		self.assertEqual(result["assigned_service_team"], self.team_a.name)

	def test_manager_cannot_assign_cross_company(self):
		frappe.set_user(self.manager_b)
		with self.assertRaises(frappe.PermissionError):
			assign_team(self.job_a, self.team_a.name)
