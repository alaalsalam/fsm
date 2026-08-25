from __future__ import annotations

import frappe
from erpnext.stock.doctype.item.test_item import make_item
from frappe.utils import nowdate

from fsm.returns import (
	create_workshop_case,
	get_return,
	list_returns,
	transition_workshop_case,
	update_workshop_case,
)
from fsm.tests.test_fire_safety import FireSafetyFixture


class WorkshopFixture(FireSafetyFixture):
	def setUp(self):
		super().setUp()
		self.warehouse = "_Test Warehouse - _TC"

	def create_case(self, **values):
		return create_workshop_case(
			self.job_a,
			self.equipment_a.name,
			"Workshop diagnosis required",
			warehouse=self.warehouse,
			**values,
		)

	def quotation(self):
		frappe.set_user("Administrator")
		return frappe.get_doc(
			{
				"doctype": "Quotation",
				"quotation_to": "Customer",
				"party_name": self.customer_a,
				"company": self.company_a,
				"transaction_date": nowdate(),
				"items": [{"item_code": self.equipment_a.item_code, "qty": 1, "rate": 100}],
			}
		).insert(ignore_permissions=True)


class TestWorkshopRMA(WorkshopFixture):
	def test_full_repair_testing_qa_dispatch_reinstall_lifecycle(self):
		frappe.set_user(self.manager_a)
		doc = self.create_case()
		for status in ("Picked Up", "Workshop Received", "Initial Inspection", "Repair In Progress"):
			doc = transition_workshop_case(doc["name"], status)
		update_workshop_case(doc["name"], repair_notes="Replaced valve and seals")
		transition_workshop_case(doc["name"], "Repair Completed")
		transition_workshop_case(doc["name"], "Testing")
		update_workshop_case(doc["name"], testing_result="Pressure held for 30 minutes")
		transition_workshop_case(doc["name"], "Quality Inspection")
		update_workshop_case(doc["name"], quality_result="Pass", final_outcome="Repaired")
		for status in ("Ready for Dispatch", "Dispatched", "Reinstalled", "Closed"):
			doc = transition_workshop_case(doc["name"], status)
		self.assertEqual(doc["status"], "Closed")
		self.assertEqual(doc["final_outcome"], "Repaired")

	def test_estimate_and_customer_approval_use_erpnext_quotation(self):
		quotation = self.quotation()
		frappe.set_user(self.manager_a)
		doc = self.create_case()
		for status in ("Picked Up", "Workshop Received", "Initial Inspection", "Estimate Required"):
			doc = transition_workshop_case(doc["name"], status)
		with self.assertRaises(frappe.ValidationError):
			transition_workshop_case(doc["name"], "Awaiting Customer Approval")
		update_workshop_case(doc["name"], quotation=quotation.name)
		doc = transition_workshop_case(doc["name"], "Awaiting Customer Approval")
		with self.assertRaises(frappe.ValidationError):
			transition_workshop_case(doc["name"], "Repair In Progress")
		update_workshop_case(doc["name"], customer_approval="Approved")
		self.assertEqual(transition_workshop_case(doc["name"], "Repair In Progress")["status"], "Repair In Progress")

	def test_workshop_receipt_is_erpnext_stock_entry(self):
		frappe.set_user("Administrator")
		item = make_item(
			f"FSM-RMA-{frappe.generate_hash(length=8).upper()}",
			properties={"is_stock_item": 1, "stock_uom": "Nos"},
		).name
		frappe.set_user(self.manager_a)
		doc = create_workshop_case(
			self.job_a,
			self.equipment_a.name,
			"Returned spare",
			items=[{"item_code": item, "qty": 1, "disposition": "Restock"}],
			warehouse=self.warehouse,
		)
		transition_workshop_case(doc["name"], "Picked Up")
		doc = transition_workshop_case(doc["name"], "Workshop Received")
		entry = frappe.get_doc("Stock Entry", doc["stock_entry"])
		self.assertEqual(entry.docstatus, 1)
		self.assertEqual(entry.purpose, "Material Receipt")
		self.assertEqual(entry.fsm_service_job, self.job_a)

	def test_required_repair_test_qa_and_outcome_evidence(self):
		frappe.set_user(self.manager_a)
		doc = self.create_case()
		for status in ("Picked Up", "Workshop Received", "Initial Inspection", "Repair In Progress"):
			doc = transition_workshop_case(doc["name"], status)
		with self.assertRaises(frappe.ValidationError):
			transition_workshop_case(doc["name"], "Repair Completed")
		update_workshop_case(doc["name"], repair_notes="Repair complete")
		transition_workshop_case(doc["name"], "Repair Completed")
		transition_workshop_case(doc["name"], "Testing")
		with self.assertRaises(frappe.ValidationError):
			transition_workshop_case(doc["name"], "Quality Inspection")

	def test_direct_create_and_cross_company_actor_are_blocked(self):
		frappe.set_user(self.technician_user_a)
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "Service Return",
					"service_job": self.job_a,
					"installed_equipment": self.equipment_a.name,
				}
			).insert()
		frappe.set_user(self.manager_b)
		with self.assertRaises(frappe.PermissionError):
			self.create_case()

	def test_scoped_projection_and_no_repair_order_duplicate(self):
		frappe.set_user(self.manager_a)
		doc = self.create_case()
		self.assertEqual(get_return(doc["name"])["installed_equipment"], self.equipment_a.name)
		self.assertEqual([row.name for row in list_returns(job=self.job_a)], [doc["name"]])
		self.assertFalse(frappe.db.exists("DocType", "Repair Order"))
