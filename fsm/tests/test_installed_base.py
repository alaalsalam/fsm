from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from fsm.api import _default_customer_group, _default_territory
from fsm.contracts.commands import transition_contract
from fsm.installed_base.api import (
	get_customer_equipment,
	get_equipment,
	get_equipment_history,
	resolve_equipment_by_qr,
)
from fsm.installed_base.commands import (
	change_equipment_status,
	confirm_installation,
	create_customer_site,
	create_equipment_location,
	create_installed_equipment,
	link_equipment_to_job,
	move_equipment_location,
)
from fsm.installed_base.provisioning import provision_delivery_note
from fsm.process.after_sales import confirm_delivery_installations, get_after_sales_setup
from fsm.service_operations.commands import create_job_from_request
from fsm.tests.test_security import SecurityFixture


def _customer(label: str) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"{label} {frappe.generate_hash(length=8)}",
				"customer_type": "Individual",
				"customer_group": _default_customer_group(),
				"territory": _default_territory(),
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _item(*, mode="Unit", serviceable=1, create_equipment=1, warranty_days=0) -> str:
	code = f"IB-{frappe.generate_hash(length=10).upper()}"
	return (
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": code,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"fsm_serviceable": serviceable,
				"fsm_create_installed_equipment": create_equipment,
				"fsm_tracking_mode": mode,
				"fsm_default_warranty_days": warranty_days,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _site(customer: str, company="_Test Company", label="Main"):
	key = frappe.generate_hash(length=8).upper()
	return create_customer_site(
		site_name=f"{label} Site",
		site_code=f"IB-SITE-{key}",
		customer=customer,
		company=company,
		status="Active",
		enabled=1,
	)


def _manual_equipment(customer: str, item_code: str, site: str | None = None, company="_Test Company"):
	return create_installed_equipment(
		equipment_name=f"Equipment {item_code}",
		company=company,
		customer=customer,
		customer_site=site,
		item_code=item_code,
	)


class TestInstalledBaseOperations(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_Test Company"
		self.customer = _customer("IB Customer")
		self.other_customer = _customer("IB Other")
		self.item = _item(warranty_days=365)
		self.site = _site(self.customer)
		self.other_site = _site(self.other_customer, label="Other")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_customer_site_and_location_hierarchy(self):
		location = create_equipment_location(
			customer_site=self.site.name,
			location_name="Lobby",
			location_code="LOBBY",
			location_type="Area",
			active=1,
		)
		child = create_equipment_location(
			customer_site=self.site.name,
			location_name="Cabinet",
			location_code="CAB-1",
			parent_location=location.name,
			location_type="Other",
			active=1,
		)
		self.assertEqual(child.parent_location, location.name)
		with self.assertRaises(frappe.ValidationError):
			create_equipment_location(
				customer_site=self.other_site.name,
				location_name="Invalid",
				location_code="BAD",
				parent_location=location.name,
				location_type="Other",
				active=1,
			)

	def test_address_ownership_requires_explicit_override(self):
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "Unlinked IB Address",
				"address_line1": "1 Test Road",
				"city": "Berlin",
				"country": "Germany",
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			create_customer_site(
				site_name="Invalid",
				site_code=f"BAD-{frappe.generate_hash(length=6)}",
				customer=self.customer,
				company=self.company,
				status="Active",
				address=address.name,
			)
		overridden = create_customer_site(
			site_name="Override",
			site_code=f"OVR-{frappe.generate_hash(length=6)}",
			customer=self.customer,
			company=self.company,
			status="Active",
			address=address.name,
			address_override_reason="Verified service-only address",
		)
		self.assertIn("Test Road", overridden.address_display)

	def test_manual_equipment_qr_warranty_and_history(self):
		frappe.db.set_single_value("Service Settings", "warranty_start_basis", "Installation Date")
		equipment = _manual_equipment(self.customer, self.item, self.site.name)
		self.assertEqual(equipment.equipment_id, equipment.name)
		self.assertEqual(equipment.qr_code, equipment.name)
		self.assertEqual(resolve_equipment_by_qr(equipment.qr_code).name, equipment.name)
		installed = confirm_installation(equipment.name, self.site.name, installation_date=nowdate())
		self.assertEqual(installed.status, "Active")
		self.assertEqual(installed.warranty_end_date, getdate(add_days(nowdate(), 365)))
		events = get_equipment_history(equipment.name)
		self.assertTrue(
			{"EquipmentProvisioned", "InstallationConfirmed", "EquipmentActivated"}.issubset(
				{event.event_type for event in events}
			)
		)

	def test_status_and_move_commands_enforce_lifecycle_and_ownership(self):
		equipment = _manual_equipment(self.customer, self.item, self.site.name)
		location = create_equipment_location(
			customer_site=self.site.name,
			location_name="Room",
			location_code="ROOM",
			location_type="Room",
			active=1,
		)
		moved = move_equipment_location(equipment.name, self.site.name, location.name, "North wall")
		self.assertEqual(moved.equipment_location, location.name)
		with self.assertRaises(frappe.ValidationError):
			move_equipment_location(equipment.name, self.other_site.name)
		self.assertEqual(
			change_equipment_status(equipment.name, "Inactive", "customer request").status, "Inactive"
		)
		with self.assertRaises(frappe.ValidationError):
			change_equipment_status(equipment.name, "Replaced")

	def test_delivery_note_unit_provisioning_is_idempotent(self):
		delivery = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"company": self.company,
				"customer": self.customer,
				"items": [{"item_code": self.item, "qty": 3, "rate": 100}],
			}
		).insert(ignore_permissions=True)
		delivery.submit()
		self.assertEqual(frappe.db.count("Installed Equipment", {"delivery_note": delivery.name}), 3)
		for _ in range(10):
			result = provision_delivery_note(delivery.name)
		self.assertEqual(result["count"], 3)
		self.assertEqual(frappe.db.count("Installed Equipment", {"delivery_note": delivery.name}), 3)
		self.assertEqual(
			frappe.db.get_value("Delivery Note", delivery.name, "fsm_provisioning_status"), "Completed"
		)
		journey = get_after_sales_setup(delivery.name)
		self.assertTrue(journey["readiness"]["equipment_provisioned"])
		self.assertFalse(journey["readiness"]["schedule_generated"])
		self.assertEqual(journey["occurrence_summary"]["total"], 0)
		self.assertEqual(journey["next_action"]["code"], "ASSIGN_SITE")

	def test_submitted_delivery_drives_contract_plan_and_schedule_review(self):
		delivery = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"company": self.company,
				"customer": self.customer,
				"items": [{"item_code": self.item, "qty": 2, "rate": 100}],
			}
		).insert(ignore_permissions=True)
		delivery.submit()
		contract_name = frappe.db.get_value("Delivery Note", delivery.name, "fsm_service_contract")
		self.assertTrue(contract_name)
		self.assertEqual(
			frappe.db.count("Service Contract", {"delivery_note": delivery.name}),
			1,
		)
		with self.assertRaises(frappe.ValidationError):
			transition_contract(contract_name, "Active")

		# Retrying the commercial workflow reuses the same contract.
		from fsm.process.commercial_after_sales import sync_delivery_contract_scope

		self.assertEqual(sync_delivery_contract_scope(delivery.name).name, contract_name)
		self.assertEqual(
			frappe.db.count("Service Contract", {"delivery_note": delivery.name}),
			1,
		)
		with self.assertRaises(frappe.ValidationError):
			confirm_delivery_installations(delivery.name, self.other_site.name)
		confirmed = confirm_delivery_installations(delivery.name, self.site.name)
		self.assertEqual(confirmed["count"], 2)
		self.assertEqual(confirm_delivery_installations(delivery.name, self.site.name)["count"], 0)

		contract = frappe.get_doc("Service Contract", contract_name)
		self.assertEqual(len(contract.covered_equipment), 2)
		transition_contract(contract.name, "Active")
		plans = frappe.get_all(
			"Maintenance Plan", filters={"service_contract": contract.name}, fields=["name", "status"]
		)
		self.assertEqual(len(plans), 1)
		self.assertEqual(plans[0].status, "Draft")
		journey = get_after_sales_setup(delivery.name)
		self.assertEqual(journey["next_action"]["code"], "APPROVE_PLANS")

	def test_delivery_note_ignores_non_serviceable_item_and_cancel_preserves_records(self):
		ignored = _item(mode="None", serviceable=0, create_equipment=0)
		delivery = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"company": self.company,
				"customer": self.customer,
				"items": [
					{"item_code": self.item, "qty": 1, "rate": 100},
					{"item_code": ignored, "qty": 2, "rate": 10},
				],
			}
		).insert(ignore_permissions=True)
		delivery.submit()
		self.assertEqual(frappe.db.count("Installed Equipment", {"delivery_note": delivery.name}), 1)
		delivery.cancel()
		self.assertEqual(frappe.db.count("Installed Equipment", {"delivery_note": delivery.name}), 1)
		self.assertEqual(
			frappe.db.get_value("Installed Equipment", {"delivery_note": delivery.name}, "status"), "Inactive"
		)
		self.assertTrue(frappe.db.exists("Service Event Log", {"event_type": "DeliveryCancelled"}))

	def test_sales_return_marks_equipment_returned_without_deleting_history(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return

		delivery = frappe.get_doc(
			{
				"doctype": "Delivery Note",
				"company": self.company,
				"customer": self.customer,
				"items": [{"item_code": self.item, "qty": 2, "rate": 100}],
			}
		).insert(ignore_permissions=True)
		delivery.submit()
		returned = make_sales_return(delivery.name)
		returned.items[0].qty = -1
		returned.insert(ignore_permissions=True)
		returned.submit()
		self.assertEqual(frappe.db.count("Installed Equipment", {"delivery_note": delivery.name}), 2)
		self.assertEqual(
			frappe.db.count("Installed Equipment", {"delivery_note": delivery.name, "status": "Returned"}), 1
		)
		self.assertTrue(frappe.db.exists("Service Event Log", {"event_type": "EquipmentReturned"}))

	def test_service_request_and_job_support_multiple_equipment(self):
		first = _manual_equipment(self.customer, self.item, self.site.name)
		second = _manual_equipment(self.customer, self.item, self.site.name)
		request = frappe.get_doc(
			{
				"doctype": "Service Request",
				"company": self.company,
				"customer": self.customer,
				"customer_site": self.site.name,
				"installed_equipment": first.name,
				"subject": "Multiple equipment",
				"status": "Open",
			}
		)
		request.flags.fsm_command = True
		request.insert(ignore_permissions=True)
		job = create_job_from_request(request.name, "ib-multi")
		link_equipment_to_job(job.name, second.name, "Inspect")
		job = frappe.get_doc("Service Job", job.name)
		self.assertEqual({row.installed_equipment for row in job.equipment}, {first.name, second.name})
		with self.assertRaises(frappe.ValidationError):
			link_equipment_to_job(job.name, second.name)
		foreign = _manual_equipment(self.other_customer, self.item, self.other_site.name)
		with self.assertRaises(frappe.ValidationError):
			link_equipment_to_job(job.name, foreign.name)

	def test_serial_validation_and_duplicate_prevention(self):
		serial_item = _item(mode="Serial")
		frappe.db.set_value("Item", serial_item, "has_serial_no", 1)
		with self.assertRaises(frappe.ValidationError):
			_manual_equipment(self.customer, serial_item, self.site.name)
		serial = frappe.get_doc(
			{
				"doctype": "Serial No",
				"serial_no": f"IB-SN-{frappe.generate_hash(length=8)}",
				"item_code": serial_item,
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		first = create_installed_equipment(
			equipment_name="Serial equipment",
			company=self.company,
			customer=self.customer,
			customer_site=self.site.name,
			item_code=serial_item,
			serial_no=serial.name,
		)
		self.assertEqual(first.serial_no, serial.name)
		with self.assertRaises((frappe.ValidationError, frappe.UniqueValidationError)):
			create_installed_equipment(
				equipment_name="Duplicate",
				company=self.company,
				customer=self.customer,
				customer_site=self.site.name,
				item_code=serial_item,
				serial_no=serial.name,
			)

	def test_real_serial_stock_delivery_provisions_bundle_serials(self):
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry

		item_code = f"IB-STOCK-{frappe.generate_hash(length=8).upper()}"
		item = make_item(
			item_code,
			properties={
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": f"{item_code}-.####",
				"fsm_serviceable": 1,
				"fsm_create_installed_equipment": 1,
				"fsm_tracking_mode": "Serial",
			},
		).name
		serials = [f"IB-SN-{frappe.generate_hash(length=10).upper()}" for _ in range(2)]
		for serial in serials:
			frappe.get_doc(
				{"doctype": "Serial No", "serial_no": serial, "item_code": item, "company": self.company}
			).insert(ignore_permissions=True)
		make_stock_entry(
			item_code=item,
			to_warehouse="_Test Warehouse - _TC",
			qty=2,
			rate=100,
			serial_no=serials,
		)
		delivery = create_delivery_note(
			item_code=item,
			customer=self.customer,
			company=self.company,
			warehouse="_Test Warehouse - _TC",
			qty=2,
			serial_no=serials,
		)
		rows = frappe.get_all(
			"Installed Equipment",
			filters={"delivery_note": delivery.name},
			fields=["customer", "item_code", "serial_no"],
			order_by="serial_no asc",
		)
		self.assertEqual([row.serial_no for row in rows], sorted(serials))
		self.assertTrue(all(row.customer == self.customer and row.item_code == item for row in rows))
		self.assertEqual(provision_delivery_note(delivery.name)["count"], 2)

	def test_guest_qr_lookup_is_denied(self):
		equipment = _manual_equipment(self.customer, self.item, self.site.name)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.AuthenticationError):
			resolve_equipment_by_qr(equipment.qr_code)


class TestInstalledBaseSecurity(SecurityFixture):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.item = _item()
		self.site_a = _site(self.customer_a, self.company_a, "A")
		self.site_b = _site(self.customer_b, self.company_b, "B")
		self.equipment_a = _manual_equipment(self.customer_a, self.item, self.site_a.name, self.company_a)
		self.equipment_b = _manual_equipment(self.customer_b, self.item, self.site_b.name, self.company_b)
		link_equipment_to_job(self.job_a, self.equipment_a.name)

	def test_customer_cannot_access_other_customer_equipment(self):
		frappe.set_user(self.customer_user_a)
		self.assertEqual([row.name for row in get_customer_equipment()], [self.equipment_a.name])
		self.assertEqual(get_equipment(self.equipment_a.name).name, self.equipment_a.name)
		with self.assertRaises(frappe.PermissionError):
			get_equipment(self.equipment_b.name)

	def test_technician_only_sees_equipment_linked_to_assigned_job(self):
		frappe.set_user(self.technician_user_a)
		self.assertEqual([row.name for row in get_customer_equipment()], [self.equipment_a.name])
		with self.assertRaises(frappe.PermissionError):
			get_equipment(self.equipment_b.name)

	def test_manager_company_scope_is_enforced(self):
		frappe.set_user(self.manager_a)
		visible = {row.name for row in get_customer_equipment()}
		self.assertIn(self.equipment_a.name, visible)
		self.assertNotIn(self.equipment_b.name, visible)
		with self.assertRaises(frappe.PermissionError):
			get_equipment(self.equipment_b.name)
