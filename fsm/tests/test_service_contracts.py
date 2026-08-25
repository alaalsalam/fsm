from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from fsm.contracts.api import get_contract, list_contracts
from fsm.contracts.commands import (
	classify_job_coverage,
	consume_entitlement,
	create_contract,
	renew_contract,
	transition_contract,
)
from fsm.contracts.coverage_engine import evaluate_coverage
from fsm.contracts.tasks import update_contract_statuses
from fsm.installed_base.commands import confirm_installation
from fsm.tests.test_installed_base import _customer, _item, _manual_equipment, _site
from fsm.tests.test_security import SecurityFixture


def _job(company: str, customer: str, equipment=None, service_type="Preventive Maintenance"):
	doc = frappe.get_doc(
		{
			"doctype": "Service Job",
			"company": company,
			"customer": customer,
			"service_type": service_type,
			"status": "Draft",
			"equipment": [{"installed_equipment": equipment}] if equipment else [],
		}
	)
	doc.flags.fsm_command = True
	return doc.insert(ignore_permissions=True)


def _contract(company: str, customer: str, *, site=None, equipment=None, classification="Contract Covered", entitlement=2):
	scope = []
	if site:
		scope.append({"customer_site": site, "installed_equipment": equipment, "active": 1})
	return create_contract(
		company=company,
		customer=customer,
		start_date=add_days(nowdate(), -30),
		end_date=add_days(nowdate(), 365),
		covered_equipment=scope,
		coverage_rules=[
			{
				"rule_name": "Standard PM",
				"service_type": "Preventive Maintenance",
				"classification": classification,
				"labour": 1,
				"parts": 0,
				"travel": 1,
				"inspection": 1,
				"active": 1,
			}
		],
		entitlements=[
			{
				"entitlement_type": "Visit",
				"service_type": "Preventive Maintenance",
				"included_quantity": entitlement,
				"active": 1,
			}
		],
	)


class TestServiceContractModel(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.customer = _customer("Contract Customer")
		self.other_customer = _customer("Other Contract Customer")
		self.site = _site(self.customer, company=self.company, label="Contract")
		self.other_site = _site(self.other_customer, company=self.company, label="Other Contract")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_contract_scope_requires_same_customer_and_company(self):
		with self.assertRaises(frappe.ValidationError):
			_contract(self.company, self.customer, site=self.other_site.name)

	def test_contract_lifecycle_is_command_owned(self):
		contract = _contract(self.company, self.customer, site=self.site.name)
		active = transition_contract(contract.name, "Active")
		self.assertEqual(active.status, "Active")
		doc = frappe.get_doc("Service Contract", contract.name)
		doc.status = "Suspended"
		with self.assertRaises(frappe.PermissionError):
			doc.save()
		self.assertEqual(transition_contract(contract.name, "Suspended").status, "Suspended")
		with self.assertRaises(frappe.ValidationError):
			transition_contract(contract.name, "Draft")

	def test_active_contract_requires_coverage_rule(self):
		contract = create_contract(
			company=self.company,
			customer=self.customer,
			start_date=nowdate(),
			end_date=add_days(nowdate(), 30),
		)
		with self.assertRaises(frappe.ValidationError):
			transition_contract(contract.name, "Active")

	def test_renewal_clones_terms_and_resets_usage(self):
		contract = _contract(self.company, self.customer, site=self.site.name)
		renewal = renew_contract(contract.name, add_days(nowdate(), 366), add_days(nowdate(), 730))
		self.assertEqual(renewal.renewed_from, contract.name)
		self.assertEqual(len(renewal.coverage_rules), 1)
		self.assertEqual(renewal.entitlements[0].used_quantity, 0)
		self.assertEqual(renewal.entitlements[0].remaining_quantity, 2)

	def test_daily_task_expires_contract_idempotently(self):
		contract = _contract(self.company, self.customer, site=self.site.name)
		doc = frappe.get_doc("Service Contract", contract.name)
		doc.end_date = add_days(nowdate(), -1)
		doc.flags.fsm_command = True
		doc.save()
		transition_contract(doc.name, "Active")
		update_contract_statuses()
		update_contract_statuses()
		self.assertEqual(frappe.db.get_value("Service Contract", doc.name, "status"), "Expired")


class TestCoverageAndEntitlements(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.customer = _customer("Coverage Customer")
		self.item = _item(warranty_days=0)
		self.site = _site(self.customer, company=self.company, label="Coverage")
		self.equipment = _manual_equipment(self.customer, self.item, self.site.name, self.company)
		self.job = _job(self.company, self.customer, self.equipment.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_contract_coverage_classifies_job_without_invoicing(self):
		contract = _contract(self.company, self.customer, site=self.site.name, equipment=self.equipment.name)
		transition_contract(contract.name, "Active")
		decision = classify_job_coverage(self.job.name, self.equipment.name)
		self.assertEqual(decision["status"], "Contract Covered")
		self.assertEqual(decision["service_contract"], contract.name)
		self.assertEqual(frappe.db.get_value("Service Job", self.job.name, "coverage_status"), "Contract Covered")
		self.assertFalse(frappe.db.exists("Sales Invoice", {"fsm_service_job": self.job.name}))

	def test_warranty_takes_precedence_over_contract(self):
		frappe.db.set_single_value("Service Settings", "warranty_start_basis", "Installation Date")
		frappe.db.set_value("Item", self.item, "fsm_default_warranty_days", 365)
		confirm_installation(self.equipment.name, self.site.name, installation_date=nowdate())
		contract = _contract(self.company, self.customer, site=self.site.name, equipment=self.equipment.name)
		transition_contract(contract.name, "Active")
		decision = evaluate_coverage(self.job.name, self.equipment.name)
		self.assertEqual(decision["status"], "Warranty")
		self.assertIsNone(decision["service_contract"])

	def test_partial_contract_and_unmatched_service(self):
		contract = _contract(
			self.company,
			self.customer,
			site=self.site.name,
			equipment=self.equipment.name,
			classification="Partially Covered",
		)
		transition_contract(contract.name, "Active")
		self.assertEqual(evaluate_coverage(self.job.name, self.equipment.name)["status"], "Partially Covered")
		self.assertEqual(
			evaluate_coverage(self.job.name, self.equipment.name, "Corrective Service")["status"],
			"Chargeable",
		)

	def test_entitlement_consumption_is_transactional_and_idempotent(self):
		contract = _contract(self.company, self.customer, site=self.site.name, entitlement=2)
		transition_contract(contract.name, "Active")
		entitlement = frappe.get_doc("Service Contract", contract.name).entitlements[0]
		first = consume_entitlement(contract.name, entitlement.name, self.job.name, "contract-retry-1")
		retry = consume_entitlement(contract.name, entitlement.name, self.job.name, "contract-retry-1")
		self.assertEqual(first.name, retry.name)
		self.assertEqual(
			frappe.db.count("Service Entitlement Consumption", {"idempotency_key": "contract-retry-1"}), 1
		)
		self.assertEqual(
			frappe.db.get_value("Service Contract Entitlement", entitlement.name, "used_quantity"), 1
		)

	def test_exhausted_entitlement_is_not_covered(self):
		contract = _contract(self.company, self.customer, site=self.site.name, entitlement=1)
		transition_contract(contract.name, "Active")
		entitlement = frappe.get_doc("Service Contract", contract.name).entitlements[0]
		consume_entitlement(contract.name, entitlement.name, self.job.name, "contract-exhaust-1")
		self.assertEqual(evaluate_coverage(self.job.name)["status"], "Not Covered")


class TestServiceContractAuthorization(SecurityFixture):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.contract_a = _contract(self.company_a, self.customer_a)
		self.contract_b = _contract(self.company_b, self.customer_b)

	def test_manager_cannot_cross_company_contract_scope(self):
		frappe.set_user(self.manager_a)
		visible = {row.name for row in list_contracts()}
		self.assertIn(self.contract_a.name, visible)
		self.assertNotIn(self.contract_b.name, visible)
		with self.assertRaises(frappe.PermissionError):
			transition_contract(self.contract_b.name, "Active")

	def test_customer_reads_only_owned_contract(self):
		frappe.set_user(self.customer_user_a)
		self.assertEqual({row.name for row in list_contracts()}, {self.contract_a.name})
		self.assertEqual(get_contract(self.contract_a.name).name, self.contract_a.name)
		with self.assertRaises(frappe.PermissionError):
			get_contract(self.contract_b.name)

	def test_technician_cannot_consume_entitlement(self):
		frappe.set_user("Administrator")
		transition_contract(self.contract_a.name, "Active")
		entitlement = frappe.get_doc("Service Contract", self.contract_a.name).entitlements[0]
		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.PermissionError):
			consume_entitlement(
				self.contract_a.name,
				entitlement.name,
				self.job_a,
				"unauthorized-contract-consumption",
			)
