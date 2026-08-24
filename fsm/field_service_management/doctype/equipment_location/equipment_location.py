import frappe
from frappe import _
from frappe.model.document import Document


class EquipmentLocation(Document):
	def before_insert(self):
		if not self.flags.fsm_command:
			frappe.throw(
				_("Equipment Locations can only be created through an application command."),
				frappe.PermissionError,
			)

	def validate(self):
		if not self.parent_location:
			return
		parent = frappe.get_cached_doc("Equipment Location", self.parent_location)
		if parent.name == self.name or parent.customer_site != self.customer_site:
			frappe.throw(_("Parent Location must belong to the same Customer Site."))
