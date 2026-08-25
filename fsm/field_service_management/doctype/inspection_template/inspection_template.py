from __future__ import annotations

import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class InspectionTemplate(Document):
	def before_insert(self):
		if self.status not in (None, "", "Draft") and not self.flags.fsm_inspection_command:
			frappe.throw(_("Inspection Templates must start in Draft."), frappe.PermissionError)

	def before_validate(self):
		self.revision = max(cint(self.revision), 1)

	def validate(self):
		before = self.get_doc_before_save()
		if before and before.status != self.status and not self.flags.fsm_inspection_command:
			frappe.throw(
				_("Inspection Template status can only change through a command."), frappe.PermissionError
			)
		if not self.items:
			frappe.throw(_("Inspection Template requires at least one item."), frappe.ValidationError)
		seen = set()
		for row in self.items:
			if row.code in seen:
				frappe.throw(_("Inspection item codes must be unique."), frappe.ValidationError)
			seen.add(row.code)
			if (
				row.response_type in {"Number", "Measurement"}
				and row.min_value is not None
				and row.max_value is not None
			):
				if flt(row.min_value) > flt(row.max_value):
					frappe.throw(_("Inspection item minimum cannot exceed maximum."), frappe.ValidationError)
			if row.response_type == "Select" and not (row.options or "").strip():
				frappe.throw(_("Select inspection items require options."), frappe.ValidationError)
		self.active = int(self.status == "Active")
		signature = self._signature()
		if before and before.template_signature and before.template_signature != signature:
			if before.status == "Active" and not self.flags.fsm_inspection_command:
				frappe.throw(
					_("Active Inspection Templates can only be revised through a command."),
					frappe.PermissionError,
				)
			self.revision = cint(before.revision) + 1
		self.template_signature = signature

	def on_trash(self):
		if frappe.db.exists("Equipment Inspection", {"inspection_template": self.name}):
			frappe.throw(_("A used Inspection Template cannot be deleted."), frappe.LinkExistsError)

	def _signature(self):
		payload = [
			(
				row.code,
				row.label,
				row.response_type,
				cint(row.required),
				flt(row.min_value) if row.min_value is not None else None,
				flt(row.max_value) if row.max_value is not None else None,
				row.options or "",
				row.measurement_unit or "",
				cint(row.evidence_required),
				row.failure_severity,
				row.action_on_fail,
			)
			for row in self.items
		]
		return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
