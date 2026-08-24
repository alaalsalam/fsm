# Copyright (c) 2026, KodLyft and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ServiceTeamMember(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		effective_from: DF.Date | None
		effective_to: DF.Date | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		role_in_team: DF.Literal["Team Leader", "Technician", "Worker", "Helper", "Specialist"]
		technician: DF.Link
	# end: auto-generated types

	pass
