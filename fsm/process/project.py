from __future__ import annotations

import frappe
from frappe import _


def validate_project_company(project: str | None, company: str | None) -> None:
	"""Keep ERPNext Project as an optional coordination link, never as FSM ownership."""
	if not project:
		return
	project_company = frappe.db.get_value("Project", project, "company")
	if project_company and project_company != company:
		frappe.throw(
			_("Project must belong to the same Company as the operational record."),
			frappe.ValidationError,
		)
