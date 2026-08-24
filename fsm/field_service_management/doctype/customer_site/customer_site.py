import frappe
from frappe import _
from frappe.model.document import Document

from fsm.installed_base.validation import contact_belongs_to_customer, validate_customer_address


class CustomerSite(Document):
	def before_insert(self):
		if not self.flags.fsm_command:
			frappe.throw(
				_("Customer Sites can only be created through an application command."),
				frappe.PermissionError,
			)

	def validate(self):
		if self.parent_site:
			parent = frappe.get_cached_doc("Customer Site", self.parent_site)
			if parent.name == self.name or parent.customer != self.customer or parent.company != self.company:
				frappe.throw(_("Parent Site must belong to the same Customer and Company."))
		validate_customer_address(
			self.customer, self.address, self.address_override_reason, self.company, self.territory
		)
		if self.primary_contact and not contact_belongs_to_customer(self.primary_contact, self.customer):
			frappe.throw(_("Primary Contact must be linked to the Site Customer."))
		self._set_address_projection()
		self._set_contact_projection()

	def _set_address_projection(self):
		if not self.address:
			self.address_display = None
			self.city = None
			return
		address = frappe.get_cached_doc("Address", self.address)
		from frappe.contacts.doctype.address.address import get_address_display

		self.address_display = get_address_display(address.as_dict())
		self.city = address.city

	def _set_contact_projection(self):
		if not self.primary_contact:
			self.contact_phone = None
			self.contact_email = None
			return
		contact = frappe.get_cached_doc("Contact", self.primary_contact)
		self.contact_phone = contact.phone or contact.mobile_no
		self.contact_email = contact.email_id
