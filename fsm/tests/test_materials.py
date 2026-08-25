from __future__ import annotations

import frappe
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

from fsm.materials import (
	get_material_plan,
	post_material_movement,
	request_shortage,
	reserve_materials,
)
from fsm.tests.test_security import SecurityFixture


class MaterialsFixture(SecurityFixture):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.warehouse = "_Test Warehouse - _TC"
		self.central = "_Test Warehouse 1 - _TC"
		self.item = make_item(
			f"FSM-MAT-{frappe.generate_hash(length=8).upper()}",
			properties={"is_stock_item": 1, "stock_uom": "Nos"},
		).name
		frappe.db.set_value("Technician", self.technician_a, "warehouse", self.warehouse)
		job = frappe.get_doc("Service Job", self.job_a)
		job.append(
			"items",
			{"item_code": self.item, "qty": 4, "rate": 99, "material_type": "Refill"},
		)
		job.flags.fsm_command = True
		job.save()
		make_stock_entry(item_code=self.item, to_warehouse=self.warehouse, qty=10, rate=25)


class TestMaterialsWorkflow(MaterialsFixture):
	def test_plan_reads_erpnext_bin_without_parallel_inventory(self):
		frappe.set_user(self.manager_a)
		plan = get_material_plan(self.job_a)
		self.assertEqual(plan["warehouse"], self.warehouse)
		self.assertEqual(plan["items"][0]["on_hand_qty"], 10)
		self.assertEqual(plan["items"][0]["required_qty"], 4)
		self.assertFalse(frappe.db.exists("DocType", "Van Inventory"))

	def test_shortage_is_an_erpnext_material_request(self):
		frappe.set_user(self.manager_a)
		result = request_shortage(self.job_a, [{"item_code": self.item, "qty": 3}])
		request = frappe.get_doc("Material Request", result["name"])
		self.assertEqual(request.fsm_service_job, self.job_a)
		self.assertEqual(request.material_request_type, "Material Transfer")
		self.assertEqual(request.items[0].warehouse, self.warehouse)

	def test_reservation_is_a_submitted_erpnext_pick_list(self):
		frappe.set_user(self.manager_a)
		result = reserve_materials(self.job_a, [{"item_code": self.item, "qty": 2}])
		pick = frappe.get_doc("Pick List", result["name"])
		self.assertEqual(pick.docstatus, 1)
		self.assertEqual(pick.fsm_service_job, self.job_a)
		self.assertEqual(pick.locations[0].warehouse, self.warehouse)
		self.assertEqual(get_material_plan(self.job_a)["items"][0]["reserved_qty"], 2)

	def test_assigned_technician_consumes_with_stock_entry_and_actual_cost_rollup(self):
		frappe.set_user(self.technician_user_a)
		result = post_material_movement(
			self.job_a,
			"Consume",
			[{"item_code": self.item, "qty": 2}],
		)
		entry = frappe.get_doc("Stock Entry", result["name"])
		self.assertEqual(entry.docstatus, 1)
		self.assertEqual(entry.purpose, "Material Issue")
		self.assertEqual(entry.fsm_material_action, "Consume")
		self.assertEqual(frappe.get_doc("Service Job", self.job_a).materials_cost, 50)
		self.assertEqual(get_material_plan(self.job_a)["items"][0]["consumed_qty"], 2)

	def test_transfer_and_unused_return_remain_standard_stock_entries(self):
		make_stock_entry(item_code=self.item, to_warehouse=self.central, qty=5, rate=25)
		frappe.set_user(self.manager_a)
		issued = post_material_movement(
			self.job_a,
			"Issue",
			[{"item_code": self.item, "qty": 1}],
			source_warehouse=self.central,
		)
		returned = post_material_movement(
			self.job_a,
			"Return",
			[{"item_code": self.item, "qty": 1}],
			target_warehouse=self.central,
		)
		self.assertEqual(frappe.db.get_value("Stock Entry", issued["name"], "purpose"), "Material Transfer")
		self.assertEqual(frappe.db.get_value("Stock Entry", returned["name"], "fsm_material_action"), "Return")

	def test_cross_company_actor_and_unlinked_visit_are_blocked(self):
		frappe.set_user(self.manager_b)
		with self.assertRaises(frappe.PermissionError):
			request_shortage(self.job_a, [{"item_code": self.item, "qty": 1}])
		frappe.set_user(self.manager_a)
		with self.assertRaises(frappe.ValidationError):
			request_shortage(
				self.job_a,
				[{"item_code": self.item, "qty": 1}],
				service_visit="missing-visit",
			)
