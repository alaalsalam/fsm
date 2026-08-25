import frappe
from frappe import _
from frappe.model.document import Document


class ServiceEntitlementConsumption(Document):
	def before_insert(self):
		if not self.flags.fsm_internal_consumption:
			frappe.throw(
				_("Entitlement consumption can only be written by the Contract application service."),
				frappe.PermissionError,
			)

	def before_save(self):
		if not self.is_new() and not self.flags.fsm_internal_consumption:
			frappe.throw(_("Entitlement Consumption is append-only."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Entitlement Consumption cannot be deleted."), frappe.PermissionError)
