# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FailureAnalysis(Document):
	def before_insert(self):
		if not self.flags.fsm_command:
			frappe.throw(_("Failure Analysis must be created through the command API."), frappe.PermissionError)

	def validate(self):
		self._guard_command_fields()
		self._validate_context()

	def _guard_command_fields(self):
		before = self.get_doc_before_save()
		if not before or self.flags.fsm_command:
			return
		frappe.throw(_("Failure Analysis changes must use the command API."), frappe.PermissionError)

	def _validate_context(self):
		job = frappe.get_cached_doc("Service Job", self.service_job)
		if not any(row.installed_equipment == self.installed_equipment for row in job.equipment):
			frappe.throw(_("Installed Equipment must be linked to the Service Job."))
		if self.service_visit and frappe.db.get_value("Service Visit", self.service_visit, "service_job") != job.name:
			frappe.throw(_("Service Visit must belong to the Service Job."))
		if self.inspection:
			inspection = frappe.db.get_value(
				"Equipment Inspection", self.inspection, ["service_job", "installed_equipment"], as_dict=True
			)
			if not inspection or inspection.service_job != job.name or inspection.installed_equipment != self.installed_equipment:
				frappe.throw(_("Inspection must match the Service Job and Installed Equipment."))
