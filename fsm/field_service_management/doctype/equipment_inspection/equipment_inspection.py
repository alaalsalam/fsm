from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class EquipmentInspection(Document):
	def before_insert(self):
		if not self.flags.fsm_inspection_command:
			frappe.throw(
				_("Equipment Inspections can only start through an inspection command."),
				frappe.PermissionError,
			)

	def validate(self):
		before = self.get_doc_before_save()
		if before and (before.status != self.status or before.overall_result != self.overall_result):
			if not self.flags.fsm_inspection_command:
				frappe.throw(
					_("Inspection outcome can only change through an inspection command."),
					frappe.PermissionError,
				)
		if before and self._response_snapshot(before) != self._response_snapshot(self):
			if not self.flags.fsm_inspection_command:
				frappe.throw(
					_("Inspection responses can only change through an inspection command."),
					frappe.PermissionError,
				)
		job = frappe.get_cached_doc("Service Job", self.service_job)
		equipment = frappe.get_cached_doc("Installed Equipment", self.installed_equipment)
		if equipment.customer != job.customer or equipment.company != job.company:
			frappe.throw(
				_("Inspection equipment must belong to the Job Customer and Company."), frappe.ValidationError
			)
		if not any(row.installed_equipment == self.installed_equipment for row in job.equipment):
			frappe.throw(_("Inspection equipment must be linked to the Service Job."), frappe.ValidationError)
		if (
			self.service_visit
			and frappe.db.get_value("Service Visit", self.service_visit, "service_job") != self.service_job
		):
			frappe.throw(_("Inspection Visit must belong to the Service Job."), frappe.ValidationError)
		if (
			self.customer != job.customer
			or self.company != job.company
			or self.customer_site != equipment.customer_site
		):
			frappe.throw(_("Inspection ownership snapshot does not match its roots."), frappe.ValidationError)

	def on_trash(self):
		frappe.throw(
			_("Equipment Inspections are durable execution evidence and cannot be deleted."),
			frappe.PermissionError,
		)

	@staticmethod
	def _response_snapshot(doc):
		return [
			(
				row.item_code,
				row.responded,
				row.response_value,
				row.numeric_value,
				str(row.date_value or ""),
				row.attachment,
				row.signature,
				row.evidence,
				row.passed,
				row.validation_message,
			)
			for row in doc.results
		]
