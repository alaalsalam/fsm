import frappe
from frappe import _
from frappe.model.document import Document


class ServiceReport(Document):
	def before_insert(self):
		if not self.flags.fsm_command:
			frappe.throw(_("Service Reports must be created through the command API."), frappe.PermissionError)

	def validate(self):
		before = self.get_doc_before_save()
		if before and before.status == "Submitted":
			frappe.throw(_("Submitted Service Reports are immutable."), frappe.PermissionError)
		if before and not self.flags.fsm_command:
			frappe.throw(_("Service Report changes must use the command API."), frappe.PermissionError)
		if self.signature_refused and not self.refusal_reason:
			frappe.throw(_("A refusal reason is required."))
		if self.customer_signature and self.signature_refused:
			frappe.throw(_("A report cannot be both signed and refused."))
