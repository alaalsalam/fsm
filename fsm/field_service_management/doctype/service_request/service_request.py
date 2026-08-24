import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ServiceRequest(Document):
	def before_insert(self):
		if not self.status:
			self.status = "Draft"
		if self.status != "Draft" and not self.flags.fsm_command:
			frappe.throw(
				_("Service Requests must enter the lifecycle in Draft through a command API."),
				frappe.PermissionError,
			)
		if self.status == "Open" and not self.opened_on:
			self.opened_on = now_datetime()

	def validate(self):
		before = self.get_doc_before_save()
		if before and before.status != self.status and not self.flags.fsm_command:
			frappe.throw(_("Service Request status can only change through a command API."))

	@frappe.whitelist()
	def create_service_job(self, idempotency_key=None):
		from fsm.service_operations.commands import create_job_from_request

		return create_job_from_request(self.name, idempotency_key).name
