import frappe
from frappe import _
from frappe.model.document import Document


class ServiceEventLog(Document):
	def before_insert(self):
		if not self.flags.fsm_internal_event:
			frappe.throw(_("Service events can only be written by the service application layer."), frappe.PermissionError)

	def before_save(self):
		if not self.is_new() and not self.flags.fsm_internal_event:
			frappe.throw(_("Service Event Log is append-only."), frappe.PermissionError)

	def before_update_after_submit(self):
		frappe.throw(_("Service Event Log is append-only."), frappe.PermissionError)

	def on_trash(self):
		if not self.flags.fsm_internal_event:
			frappe.throw(_("Service Event Log entries cannot be deleted."), frappe.PermissionError)
