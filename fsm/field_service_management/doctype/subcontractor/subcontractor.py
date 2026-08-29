# Copyright (c) 2026, DIGIT and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Subcontractor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		contact_person: DF.Data | None
		email: DF.Data | None
		hourly_rate: DF.Currency
		notes: DF.Text | None
		phone: DF.Data | None
		status: DF.Literal["Active", "Inactive"]
		subcontractor_name: DF.Data
		territory: DF.Link | None
	# end: auto-generated types

	def before_validate(self):
		if not self.company:
			self.company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
				"company"
			)
