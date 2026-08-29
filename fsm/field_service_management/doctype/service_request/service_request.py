import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class ServiceRequest(Document):
	def before_validate(self):
		self._set_default_company()

	def _set_default_company(self):
		"""Keep Desk, imports, and API-created requests on the active Company."""
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
				"company"
			)

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
		from fsm.process.project import validate_project_company

		validate_project_company(self.project, self.company)
		before = self.get_doc_before_save()
		if before and before.status != self.status and not self.flags.fsm_command:
			frappe.throw(_("Service Request status can only change through a command API."))
		if self.customer_site:
			site = frappe.get_cached_doc("Customer Site", self.customer_site)
			if not self.customer or site.customer != self.customer or site.company != self.company:
				frappe.throw(_("Customer Site must belong to the Request Customer and Company."))
		if self.installed_equipment:
			equipment = frappe.get_cached_doc("Installed Equipment", self.installed_equipment)
			if not self.customer or equipment.customer != self.customer or equipment.company != self.company:
				frappe.throw(_("Installed Equipment must belong to the Request Customer and Company."))
			if self.customer_site and equipment.customer_site != self.customer_site:
				frappe.throw(_("Installed Equipment must belong to the selected Customer Site."))

	@frappe.whitelist()
	def create_service_job(self, idempotency_key=None):
		from fsm.service_operations.commands import create_job_from_request

		return create_job_from_request(self.name, idempotency_key).name
