# Copyright (c) 2026, DIGIT and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate

STOCKED_DISPOSITIONS = ("Restock", "Refurbish")


class ServiceReturn(Document):
	def before_insert(self):
		if not self.flags.fsm_command:
			frappe.throw(_("Workshop/RMA cases must be created through the command API."), frappe.PermissionError)

	def validate(self):
		if not self.return_date:
			self.return_date = nowdate()
		self._guard_command_changes()
		self._validate_context()

	def _guard_command_changes(self):
		if self.get_doc_before_save() and not self.flags.fsm_command:
			frappe.throw(_("Workshop/RMA changes must use the command API."), frappe.PermissionError)

	def _validate_context(self):
		job = frappe.get_cached_doc("Service Job", self.service_job)
		if self.installed_equipment and not any(
			row.installed_equipment == self.installed_equipment for row in job.equipment
		):
			frappe.throw(_("Installed Equipment must be linked to the Service Job."))
		if self.warehouse:
			company = frappe.db.get_value("Warehouse", self.warehouse, "company")
			if company != job.company:
				frappe.throw(_("Workshop Warehouse must belong to the Service Job company."))
		for doctype, field in (("Quotation", "quotation"), ("Sales Invoice", "sales_invoice")):
			name = self.get(field)
			if name and frappe.db.get_value(doctype, name, "company") != job.company:
				frappe.throw(_("Commercial documents must belong to the Service Job company."))

	@frappe.whitelist()
	def approve(self):
		"""Compatibility adapter: accept the pickup request."""
		return self._compat_transition("Pickup Requested", "Picked Up")

	@frappe.whitelist()
	def receive(self):
		"""Compatibility adapter: receive picked-up material/equipment into workshop."""
		from fsm.security.policy import require_job_access

		require_job_access(self.service_job, "write", manager_only=True)
		self._guard_status(("Picked Up",), _("Only a picked-up case can be workshop received."))
		if not self.warehouse:
			frappe.throw(_("Set a Workshop Warehouse before receiving the case."))
		receipt_items = [row for row in self.items if row.disposition in STOCKED_DISPOSITIONS]
		if receipt_items and not self.stock_entry:
			self.stock_entry = _make_receipt(self, receipt_items)
		self.status = "Workshop Received"
		self.flags.fsm_command = True
		self.save()
		return self.as_dict()

	@frappe.whitelist()
	def close(self):
		return self._compat_transition("Reinstalled", "Closed")

	def _compat_transition(self, expected: str, target: str):
		from fsm.security.policy import require_job_access

		require_job_access(self.service_job, "write", manager_only=True)
		self._guard_status((expected,), _("This action is not valid for the current workshop state."))
		self.status = target
		self.flags.fsm_command = True
		self.save()
		return self.as_dict()

	def _guard_status(self, allowed: tuple, message: str):
		if self.status not in allowed:
			frappe.throw(message)


def _make_receipt(doc: "ServiceReturn", items) -> str:
	"""Create & submit an ERPNext Material Receipt for workshop-received stock rows."""
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Receipt"
	se.purpose = "Material Receipt"
	se.posting_date = doc.return_date
	se.company = frappe.db.get_value("Service Job", doc.service_job, "company")
	se.fsm_service_job = doc.service_job
	se.fsm_material_action = "Return"
	for row in items:
		se.append(
			"items",
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"uom": row.uom or None,
				"t_warehouse": doc.warehouse,
				"allow_zero_valuation_rate": 1,
				"fsm_installed_equipment": doc.installed_equipment,
			},
		)
	# Manager Job authorization and Approved transition guard are established by receive().
	se.flags.ignore_permissions = True
	se.insert()
	se.submit()
	return se.name
