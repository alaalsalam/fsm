import frappe
from frappe import _
from frappe.model.document import Document

from fsm.installed_base.validation import validate_equipment_links
from fsm.installed_base.warranty import apply_warranty_projection


class InstalledEquipment(Document):
	def before_validate(self):
		# Frappe validates mandatory fields before `before_insert`; autoname has already
		# assigned the stable service-asset identity at this point.
		if self.is_new() and self.name:
			self.equipment_id = self.equipment_id or self.name
			self.qr_code = self.qr_code or self.equipment_id

	def before_insert(self):
		if not self.flags.fsm_command:
			frappe.throw(
				_("Installed Equipment can only be created through an application command."),
				frappe.PermissionError,
			)

	def validate(self):
		before = self.get_doc_before_save()
		if before and before.status != self.status and not self.flags.fsm_command:
			frappe.throw(_("Equipment status can only change through a command API."), frappe.PermissionError)
		validate_equipment_links(self)
		apply_warranty_projection(self)

	def on_trash(self):
		if frappe.db.exists("Service Job Equipment", {"installed_equipment": self.name}):
			frappe.throw(_("Equipment used by a Service Job cannot be deleted."), frappe.LinkExistsError)
