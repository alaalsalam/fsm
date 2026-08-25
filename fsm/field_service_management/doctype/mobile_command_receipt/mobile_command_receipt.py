import frappe
from frappe import _
from frappe.model.document import Document


class MobileCommandReceipt(Document):
	def before_insert(self):
		if not self.flags.fsm_offline_command:
			frappe.throw(_("Mobile command receipts are server managed."), frappe.PermissionError)

	def validate(self):
		if not self.flags.fsm_offline_command:
			frappe.throw(_("Mobile command receipts are immutable."), frappe.PermissionError)
