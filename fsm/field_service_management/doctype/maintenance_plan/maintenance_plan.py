from __future__ import annotations

import hashlib
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_timedelta, getdate


class MaintenancePlan(Document):
	def before_insert(self):
		if self.status not in (None, "", "Draft") and not self.flags.fsm_command:
			frappe.throw(
				_("Maintenance Plans must start in Draft through an application command."),
				frappe.PermissionError,
			)

	def before_validate(self):
		self.revision = max(cint(self.revision), 1)

	def validate(self):
		self._guard_status_change()
		self._validate_period_and_timezone()
		self._validate_site_and_contract()
		self._validate_equipment()
		self._validate_lines()
		self._set_schedule_signature()
		self.active = int(self.status == "Active")

	def _set_schedule_signature(self):
		signature = self._signature()
		before = self.get_doc_before_save()
		if before and before.schedule_signature and before.schedule_signature != signature:
			if before.status == "Active" and not self.flags.fsm_command:
				frappe.throw(
					_("An Active Maintenance Plan can only be revised through a command API."),
					frappe.PermissionError,
				)
			self.revision = cint(before.revision) + 1
		self.schedule_signature = signature

	def on_update(self):
		before = self.get_doc_before_save()
		if before and cint(before.revision) != cint(self.revision):
			from fsm.maintenance.engine import supersede_revision

			supersede_revision(self.name, cint(before.revision), cint(self.revision))

	def on_trash(self):
		if frappe.db.exists("Maintenance Occurrence", {"maintenance_plan": self.name}):
			frappe.throw(_("A Maintenance Plan with occurrences cannot be deleted."), frappe.LinkExistsError)

	def _guard_status_change(self):
		before = self.get_doc_before_save()
		if before and before.status != self.status and not self.flags.fsm_command:
			frappe.throw(
				_("Maintenance Plan status can only change through a command API."), frappe.PermissionError
			)

	def _validate_period_and_timezone(self):
		if self.end_date and getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Maintenance Plan Start Date cannot be after End Date."), frappe.ValidationError)
		try:
			ZoneInfo(self.timezone)
		except ZoneInfoNotFoundError:
			frappe.throw(_("Select a valid IANA timezone."), frappe.ValidationError)
		if cint(self.forecast_horizon_days) < 1 or cint(self.forecast_horizon_days) > 1095:
			frappe.throw(_("Forecast Horizon must be between 1 and 1095 days."), frappe.ValidationError)
		if cint(self.due_window_days) < 1 or cint(self.due_window_days) > 31:
			frappe.throw(_("Job Grouping Window must be between 1 and 31 days."), frappe.ValidationError)

	def _validate_site_and_contract(self):
		site = frappe.get_cached_doc("Customer Site", self.customer_site)
		if site.customer != self.customer or site.company != self.company:
			frappe.throw(
				_("Maintenance Plan Site must belong to the Customer and Company."), frappe.ValidationError
			)
		if self.service_contract:
			contract = frappe.get_cached_doc("Service Contract", self.service_contract)
			if contract.customer != self.customer or contract.company != self.company:
				frappe.throw(
					_("Maintenance Plan Contract must belong to the Customer and Company."),
					frappe.ValidationError,
				)
			if self.status == "Active" and contract.status != "Active":
				frappe.throw(
					_("An Active Maintenance Plan requires an Active Service Contract."),
					frappe.ValidationError,
				)

	def _validate_equipment(self):
		if not self.equipment:
			frappe.throw(
				_("Maintenance Plan requires at least one Installed Equipment record."),
				frappe.ValidationError,
			)
		seen = set()
		for row in self.equipment:
			if row.installed_equipment in seen:
				frappe.throw(
					_("Installed Equipment cannot appear twice on a Maintenance Plan."),
					frappe.ValidationError,
				)
			seen.add(row.installed_equipment)
			equipment = frappe.get_cached_doc("Installed Equipment", row.installed_equipment)
			if (
				equipment.customer != self.customer
				or equipment.company != self.company
				or equipment.customer_site != self.customer_site
			):
				frappe.throw(
					_("Plan Equipment must belong to the Plan Customer, Company, and Site."),
					frappe.ValidationError,
				)
			if equipment.status in {"Returned", "Replaced", "Disposed"}:
				frappe.throw(
					_("Terminal equipment cannot be scheduled for maintenance."), frappe.ValidationError
				)
			row.customer_site = equipment.customer_site
			row.item_code = equipment.item_code
			row.item_group = equipment.item_group

	def _validate_lines(self):
		if not self.lines:
			frappe.throw(
				_("Maintenance Plan requires at least one active Plan Line."), frappe.ValidationError
			)
		seen = set()
		plan_equipment = {row.installed_equipment: row for row in self.equipment if row.active}
		for row in self.lines:
			if row.line_code in seen:
				frappe.throw(_("Plan Line Code must be unique within the Plan."), frappe.ValidationError)
			seen.add(row.line_code)
			if cint(row.interval_count) < 1:
				frappe.throw(_("Maintenance interval must be at least one."), frappe.ValidationError)
			if row.first_due_date and getdate(row.first_due_date) < getdate(self.start_date):
				frappe.throw(
					_("Plan Line First Due Date cannot be before the Plan Start Date."),
					frappe.ValidationError,
				)
			if row.equipment_scope == "Single Equipment" and row.installed_equipment not in plan_equipment:
				frappe.throw(
					_("Single Equipment scope must select equipment from the Plan."), frappe.ValidationError
				)
			if row.equipment_scope == "Item Group" and not row.item_group:
				frappe.throw(_("Item Group scope requires an Item Group."), frappe.ValidationError)
			if row.equipment_scope == "Item Group" and not any(
				item.item_group == row.item_group for item in plan_equipment.values()
			):
				frappe.throw(
					_("Item Group scope does not match any active Plan Equipment."), frappe.ValidationError
				)

	def _signature(self) -> str:
		payload = {
			"start_date": str(self.start_date or ""),
			"end_date": str(self.end_date or ""),
			"timezone": self.timezone or "UTC",
			"forecast_horizon_days": cint(self.forecast_horizon_days),
			"due_window_days": cint(self.due_window_days),
			"catch_up_policy": self.catch_up_policy,
			"dst_policy": self.dst_policy,
			"equipment": sorted((row.installed_equipment, cint(row.active)) for row in self.equipment),
			"lines": sorted(
				(
					row.line_code,
					row.service_type,
					cint(row.interval_count),
					row.interval_unit,
					str(row.first_due_date or ""),
					int(get_timedelta(row.scheduled_time).total_seconds()) if row.scheduled_time else 0,
					row.equipment_scope,
					row.item_group or "",
					row.installed_equipment or "",
					cint(row.lead_days),
					cint(row.grace_days),
					cint(row.auto_release_job),
					cint(row.active),
				)
				for row in self.lines
			),
		}
		return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
