from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, nowdate


class ServiceContract(Document):
	def before_validate(self):
		if self.name and not self.name.startswith("new-"):
			self.contract_no = self.name

	def before_insert(self):
		if self.status not in (None, "", "Draft") and not self.flags.fsm_command:
			frappe.throw(
				_("Service Contracts must enter the lifecycle in Draft through an application command."),
				frappe.PermissionError,
			)

	def validate(self):
		self._guard_status_change()
		self._validate_period()
		self._validate_scope()
		self._validate_coverage_rules()
		self._validate_entitlements()
		self._validate_commercial_references()
		self._set_renewal_projection()

	def on_trash(self):
		if frappe.db.exists("Service Job", {"service_contract": self.name}) or frappe.db.exists(
			"Service Entitlement Consumption", {"service_contract": self.name}
		):
			frappe.throw(_("A Service Contract used by operations cannot be deleted."), frappe.LinkExistsError)

	def _guard_status_change(self):
		before = self.get_doc_before_save()
		if before and before.status != self.status and not self.flags.fsm_command:
			frappe.throw(
				_("Service Contract status can only change through a command API."),
				frappe.PermissionError,
			)

	def _validate_period(self):
		if self.start_date and self.end_date and getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("Contract Start Date cannot be after End Date."), frappe.ValidationError)

	def _validate_scope(self):
		seen: set[tuple[str, str, str]] = set()
		for row in self.covered_equipment:
			if row.installed_equipment:
				equipment = frappe.get_cached_doc("Installed Equipment", row.installed_equipment)
				if equipment.customer != self.customer or equipment.company != self.company:
					frappe.throw(
						_("Covered Equipment must belong to the Contract Customer and Company."),
						frappe.ValidationError,
					)
				if row.customer_site and equipment.customer_site != row.customer_site:
					frappe.throw(
						_("Covered Equipment must belong to the selected Customer Site."),
						frappe.ValidationError,
					)
				row.customer_site = equipment.customer_site
				row.item_group = row.item_group or equipment.item_group
			if not row.customer_site:
				frappe.throw(_("Every coverage scope row requires a Customer Site."), frappe.ValidationError)
			site = frappe.get_cached_doc("Customer Site", row.customer_site)
			if site.customer != self.customer or site.company != self.company:
				frappe.throw(
					_("Covered Site must belong to the Contract Customer and Company."),
					frappe.ValidationError,
				)
			key = (row.customer_site or "", row.installed_equipment or "", row.item_group or "")
			if key in seen:
				frappe.throw(_("Duplicate Contract coverage scope row."), frappe.ValidationError)
			seen.add(key)

	def _validate_coverage_rules(self):
		if self.status == "Active" and not any(row.active for row in self.coverage_rules):
			frappe.throw(_("An Active Contract requires at least one active Coverage Rule."))
		seen: set[tuple[str, str]] = set()
		for row in self.coverage_rules:
			key = (row.service_type or "", row.item_group or "")
			if row.active and key in seen:
				frappe.throw(
					_("Only one active Coverage Rule is allowed for the same Service Type and Item Group."),
					frappe.ValidationError,
				)
			if row.active:
				seen.add(key)
			if row.limits_json:
				try:
					value = json.loads(row.limits_json)
				except (TypeError, ValueError):
					frappe.throw(_("Coverage limits must be a valid JSON object."), frappe.ValidationError)
				if not isinstance(value, dict):
					frappe.throw(_("Coverage limits must be a JSON object."), frappe.ValidationError)

	def _validate_entitlements(self):
		seen: set[tuple[str, str, str, str]] = set()
		for row in self.entitlements:
			if flt(row.used_quantity) > flt(row.included_quantity):
				frappe.throw(_("Used entitlement cannot exceed the included quantity."), frappe.ValidationError)
			if row.period_start and row.period_end and getdate(row.period_start) > getdate(row.period_end):
				frappe.throw(_("Entitlement Period Start cannot be after Period End."), frappe.ValidationError)
			row.remaining_quantity = max(flt(row.included_quantity) - flt(row.used_quantity), 0)
			key = (
				row.entitlement_type or "",
				row.service_type or "",
				str(row.period_start or ""),
				str(row.period_end or ""),
			)
			if row.active and key in seen:
				frappe.throw(_("Duplicate active Contract entitlement."), frappe.ValidationError)
			if row.active:
				seen.add(key)

	def _validate_commercial_references(self):
		for fieldname, doctype in (
			("quotation", "Quotation"),
			("sales_order", "Sales Order"),
			("sales_invoice", "Sales Invoice"),
			("renewal_quotation", "Quotation"),
		):
			name = self.get(fieldname)
			if not name:
				continue
			company, customer = frappe.db.get_value(doctype, name, ["company", "party_name" if doctype == "Quotation" else "customer"])
			if company != self.company or customer != self.customer:
				frappe.throw(
					_("{0} must belong to the Contract Customer and Company.").format(self.meta.get_label(fieldname)),
					frappe.ValidationError,
				)

	def _set_renewal_projection(self):
		if not self.end_date or self.status in {"Cancelled", "Expired"}:
			self.expiring_soon = 0
			return
		self.expiring_soon = int(getdate(self.end_date) <= getdate(add_days(nowdate(), 30)))
		if self.expiring_soon:
			self.renewal_recommended = 1
