import frappe
from frappe import _
from frappe.model.document import Document


class ServiceVisit(Document):
	def before_insert(self):
		if not self.flags.fsm_command:
			frappe.throw(_("Service Visits must be created through create_visit."), frappe.PermissionError)

	def validate(self):
		before = self.get_doc_before_save()
		if before and before.status != self.status and not self.flags.fsm_command:
			frappe.throw(_("Service Visit status can only change through a command API."))
		if self.scheduled_start and self.scheduled_end and self.scheduled_end < self.scheduled_start:
			frappe.throw(_("Scheduled end must be after scheduled start."))
