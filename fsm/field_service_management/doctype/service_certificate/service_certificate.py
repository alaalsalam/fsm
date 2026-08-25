import frappe
from frappe import _
from frappe.model.document import Document


class ServiceCertificate(Document):
	def before_insert(self):
		if not self.flags.fsm_command:
			frappe.throw(_("Service Certificates must be created through the command API."), frappe.PermissionError)

	def validate(self):
		if self.get_doc_before_save() and not self.flags.fsm_command:
			frappe.throw(_("Service Certificate changes must use the command API."), frappe.PermissionError)
