# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class ServiceJob(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from fsm.field_service_management.doctype.service_job_equipment.service_job_equipment import (
			ServiceJobEquipment,
		)
		from fsm.field_service_management.doctype.service_job_item.service_job_item import ServiceJobItem
		from fsm.field_service_management.doctype.service_job_task.service_job_task import ServiceJobTask

		address_display: DF.SmallText | None
		checklist_template: DF.Link | None
		company: DF.Link
		completed_on: DF.Datetime | None
		contact: DF.Link | None
		coverage_reason: DF.SmallText | None
		coverage_status: DF.Literal[
			"Warranty", "Contract Covered", "Partially Covered", "Chargeable", "FOC", "Not Covered"
		] | None
		covered_labour: DF.Check
		covered_parts: DF.Check
		covered_travel: DF.Check
		customer: DF.Link
		customer_name: DF.Data | None
		items: DF.Table[ServiceJobItem]
		equipment: DF.Table[ServiceJobEquipment]
		naming_series: DF.Literal["FSM-JOB-.YYYY.-"]
		notes: DF.Text | None
		primary_technician: DF.Link | None
		priority: DF.Literal["Low", "Medium", "High", "Urgent"]
		promised_response_by: DF.Datetime | None
		quotation: DF.Link | None
		responded_on: DF.Datetime | None
		sales_invoice: DF.Link | None
		service_contract: DF.Link | None
		scheduled_date: DF.Datetime | None
		scheduled_end: DF.Datetime | None
		service_address: DF.Link | None
		service_latitude: DF.Float
		service_longitude: DF.Float
		service_type: DF.Data | None
		sla_breached: DF.Check
		status: DF.Literal[
			"Draft", "Planned", "Scheduled", "Dispatched", "In Progress", "On Hold", "Completed", "Cancelled"
		]
		tasks: DF.Table[ServiceJobTask]
		territory: DF.Link | None
		total_amount: DF.Currency
	# end: auto-generated types

	def before_insert(self):
		if self.status not in (None, "", "Draft") and not self.flags.fsm_command:
			frappe.throw(_("Service Jobs must enter the lifecycle in Draft through an application command."))

	def validate(self):
		self.guard_lifecycle_changes()
		self.apply_settings_defaults()
		self.apply_checklist_template()
		self.set_address_display()
		self.calculate_totals()
		self.validate_equipment_rows()
		self.validate_service_contract()
		self.normalize_tasks()
		self.set_completion_timestamp()
		self.track_sla()
		self.calculate_costs()

	def validate_equipment_rows(self):
		seen = set()
		for row in self.equipment:
			if row.installed_equipment in seen:
				frappe.throw(_("Installed Equipment cannot appear twice on the same Service Job."))
			seen.add(row.installed_equipment)
			equipment = frappe.get_cached_doc("Installed Equipment", row.installed_equipment)
			if equipment.customer != self.customer or equipment.company != self.company:
				frappe.throw(_("Installed Equipment must belong to the Job Customer and Company."))
			if equipment.status in {"Returned", "Replaced", "Disposed"}:
				frappe.throw(_("Terminal equipment cannot be added to a Service Job."))
			row.customer_site = equipment.customer_site
			row.equipment_location = equipment.equipment_location
			row.item_code = equipment.item_code
			row.serial_no = equipment.serial_no
			row.equipment_status = equipment.status

	def validate_service_contract(self):
		if not self.service_contract:
			return
		contract = frappe.get_cached_doc("Service Contract", self.service_contract)
		if contract.customer != self.customer or contract.company != self.company:
			frappe.throw(_("Service Contract must belong to the Job Customer and Company."))
		before = self.get_doc_before_save()
		if (not before or before.service_contract != self.service_contract) and contract.status != "Active":
			frappe.throw(_("Only an Active Service Contract can be assigned to a Service Job."))

	def calculate_costs(self):
		"""Roll up labour + materials + overhead into the job's cost fields.
		Actual hours come from Service Time Log entries (see fsm.costing)."""
		from fsm.costing import compute_costs

		for field, value in compute_costs(self).items():
			setattr(self, field, value)

	def on_update(self):
		self.sync_technician_status()
		self.autocreate_invoice_if_enabled()
		self.notify_reschedule()

	def notify_reschedule(self):
		"""Post a System message to the job thread when the service schedule moves, so
		the customer sees it on the portal (FSM feature #11)."""
		before = self.get_doc_before_save()
		if not before or not self.scheduled_date:
			return
		if before.scheduled_date == self.scheduled_date:
			return
		from frappe.utils import format_datetime

		from fsm.messaging import post_system_message

		post_system_message(
			self.name, _("Service schedule changed to {0}.").format(format_datetime(self.scheduled_date))
		)

	@frappe.whitelist()
	def start_task(self, idx: int):
		"""Begin a checklist step. Steps must be started in order."""
		from fsm.security.policy import require_job_access

		require_job_access(self, "write")
		idx = int(idx)
		self._guard_sequence(idx)
		for t in self.tasks:
			if t.idx == idx:
				if t.status == "Done":
					frappe.throw("This step is already done.")
				t.status = "In Progress"
				t.started_on = t.started_on or now_datetime()
				break
		self.save()
		return self.as_dict()

	@frappe.whitelist()
	def complete_task(self, idx: int, note: str | None = None):
		"""Finish a checklist step (the earlier steps must be done first)."""
		from fsm.security.policy import require_job_access

		require_job_access(self, "write")
		idx = int(idx)
		self._guard_sequence(idx)
		for t in self.tasks:
			if t.idx == idx:
				t.status = "Done"
				t.completed = 1
				t.completed_on = now_datetime()
				if not t.started_on:
					t.started_on = now_datetime()
				if note:
					t.note = note
				break
		self.save()
		return self.as_dict()

	def guard_lifecycle_changes(self):
		before = self.get_doc_before_save()
		if not before or self.flags.fsm_command:
			return
		if before.status != self.status or before.phase != self.phase:
			frappe.throw(_("Service Job lifecycle can only change through a command API."))

	def _guard_sequence(self, idx: int):
		for t in self.tasks:
			if t.idx < idx and t.status != "Done":
				frappe.throw("Complete the previous step first.")

	def apply_settings_defaults(self):
		"""Fall back to Service Settings for the unset operational defaults."""
		settings = frappe.get_cached_doc("Service Settings")
		if not self.territory and settings.default_territory:
			self.territory = settings.default_territory
		if not self.checklist_template and settings.default_checklist_template:
			self.checklist_template = settings.default_checklist_template
		if not self.priority and settings.default_priority:
			self.priority = settings.default_priority

	def apply_checklist_template(self):
		"""Seed the task list from the linked template the first time it's set."""
		if self.checklist_template and not self.tasks:
			template = frappe.get_doc("Checklist Template", self.checklist_template)
			for row in template.items:
				self.append("tasks", {"task": row.task, "note": row.description})

	def calculate_totals(self):
		total = 0.0
		for item in self.items:
			item.amount = (item.qty or 0) * (item.rate or 0)
			total += item.amount
		self.total_amount = total

	def set_address_display(self):
		"""Pull the customer's primary address when none is set, then render it."""
		if not self.service_address and self.customer:
			self.service_address = _primary_customer_address(self.customer)

		if self.service_address:
			from frappe.contacts.doctype.address.address import get_address_display

			self.address_display = get_address_display(
				frappe.get_doc("Address", self.service_address).as_dict()
			)
		else:
			self.address_display = None

	def normalize_tasks(self):
		"""Keep each task's completed flag + timestamps consistent with its status."""
		for t in self.tasks:
			if t.status == "Done":
				t.completed = 1
				if not t.completed_on:
					t.completed_on = now_datetime()
				if not t.started_on:
					t.started_on = t.completed_on
			elif t.status == "In Progress":
				t.completed = 0
				t.completed_on = None
				if not t.started_on:
					t.started_on = now_datetime()
			else:
				t.completed = 0
				t.started_on = None
				t.completed_on = None

	def set_completion_timestamp(self):
		if self.status == "Completed" and not self.completed_on:
			self.completed_on = now_datetime()
		elif self.status != "Completed":
			self.completed_on = None

	def track_sla(self):
		"""Stamp the first response and flag SLA breaches against promised_response_by.
		A 'response' is the job leaving the Draft/Scheduled backlog (Assigned onward)."""
		responded_statuses = ("Dispatched", "In Progress", "On Hold", "Completed")
		if not self.responded_on and self.status in responded_statuses:
			self.responded_on = now_datetime()

		if self.responded_on or not self.promised_response_by:
			self.sla_breached = 0
		else:
			self.sla_breached = 1 if now_datetime() > get_datetime(self.promised_response_by) else 0

	def sync_technician_status(self):
		"""Keep the assigned technician's availability in step with the job."""
		if not self.primary_technician:
			return
		target = None
		if self.status == "In Progress":
			target = "On Job"
		elif self.status in ("Completed", "Cancelled"):
			target = "Available"
		if not target:
			return
		current = frappe.db.get_value("Technician", self.primary_technician, "status")
		if current and current not in (target, "Off Duty"):
			frappe.db.set_value("Technician", self.primary_technician, "status", target)

	def autocreate_invoice_if_enabled(self):
		"""On completion, raise the Sales Invoice automatically if configured."""
		if self.status != "Completed" or self.sales_invoice or not self.items:
			return
		if not frappe.db.get_single_value("Service Settings", "auto_create_invoice"):
			return
		try:
			make_invoice_from_job(self.name, system_operation=True)
		except Exception:
			frappe.log_error(
				title="FSM auto-invoice failed",
				message=frappe.get_traceback(),
			)


def _primary_customer_address(customer: str) -> str | None:
	"""Best-effort lookup of a customer's primary/billing Address."""
	from frappe.contacts.doctype.address.address import get_default_address

	return get_default_address("Customer", customer)


def make_invoice_from_job(job: str, *, system_operation: bool = False) -> str:
	"""Create (once) a draft Sales Invoice from a job's parts & services.

	Shared by the console action (`fsm.api.create_invoice_from_job`) and the
	auto-invoice-on-completion flow. Idempotent: returns the existing invoice
	if the job already has one."""
	doc = frappe.get_doc("Service Job", job)
	if not system_operation:
		from fsm.security.policy import require_job_access

		require_job_access(doc, "write", manager_only=True)

	if doc.sales_invoice:
		return doc.sales_invoice
	if not doc.customer:
		frappe.throw("This job has no customer to invoice.")
	if not doc.items:
		frappe.throw("This job has no parts or services to invoice.")

	invoice = frappe.new_doc("Sales Invoice")
	invoice.customer = doc.customer
	invoice.company = doc.company
	invoice.po_no = doc.name
	for row in doc.items:
		invoice.append(
			"items",
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"rate": row.rate,
				"uom": row.uom or None,
			},
		)
	if system_operation:
		invoice.insert(ignore_permissions=True)
	else:
		invoice.insert()

	doc.db_set("sales_invoice", invoice.name)
	return invoice.name
