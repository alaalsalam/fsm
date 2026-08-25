import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, cint, getdate

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
		if before and not self.flags.fsm_command:
			service_fields = (
				"last_refill_date",
				"last_refill_result",
				"last_hydro_test_date",
				"hydro_due_date",
			)
			if any(before.get(field) != self.get(field) for field in service_fields):
				frappe.throw(
					_("Fire safety service history can only change through a command API."),
					frappe.PermissionError,
				)
		validate_equipment_links(self)
		apply_warranty_projection(self)
		self._validate_fire_safety_profile()

	def on_trash(self):
		if frappe.db.exists("Service Job Equipment", {"installed_equipment": self.name}):
			frappe.throw(_("Equipment used by a Service Job cannot be deleted."), frappe.LinkExistsError)

	def _validate_fire_safety_profile(self):
		if self.equipment_category != "Fire Extinguisher":
			return
		if (
			self.manufacturing_date
			and self.expiry_date
			and getdate(self.manufacturing_date) > getdate(self.expiry_date)
		):
			frappe.throw(_("Manufacturing Date cannot be after Expiry Date."), frappe.ValidationError)
		if cint(self.hydro_test_interval_months) < 1:
			frappe.throw(_("Hydro Test Interval must be at least one month."), frappe.ValidationError)
		basis = self.last_hydro_test_date or self.manufacturing_date
		self.hydro_due_date = add_months(basis, cint(self.hydro_test_interval_months)) if basis else None
