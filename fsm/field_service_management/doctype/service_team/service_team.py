# Copyright (c) 2026, DIGIT and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class ServiceTeam(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from fsm.field_service_management.doctype.service_team_member.service_team_member import (
			ServiceTeamMember,
		)

		active: DF.Check
		capacity: DF.Int
		company: DF.Link
		default_warehouse: DF.Link | None
		effective_from: DF.Date | None
		effective_to: DF.Date | None
		members: DF.Table[ServiceTeamMember]
		notes: DF.Text | None
		status: DF.Literal["Active", "Inactive", "Suspended"]
		team_leader: DF.Link | None
		team_name: DF.Data
		territory: DF.Link | None
		vehicle: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self._validate_team_window()
		self._validate_members()
		self._validate_leader()
		self._validate_no_overlapping_membership()

	def _validate_team_window(self):
		if self.effective_from and self.effective_to and getdate(self.effective_from) > getdate(self.effective_to):
			frappe.throw(_("Effective From cannot be after Effective To."), frappe.ValidationError)

	def _validate_members(self):
		seen: set[str] = set()
		technicians = [m.technician for m in self.members if m.technician]
		company_map = _technician_company_map(technicians)
		for member in self.members:
			if not member.technician:
				continue
			if member.technician in seen:
				frappe.throw(
					_("{0} is listed more than once on this team.").format(member.technician),
					frappe.ValidationError,
				)
			seen.add(member.technician)

			if company_map.get(member.technician) != self.company:
				frappe.throw(
					_("Member {0} does not belong to company {1}.").format(member.technician, self.company),
					frappe.ValidationError,
				)

			if (
				member.effective_from
				and member.effective_to
				and getdate(member.effective_from) > getdate(member.effective_to)
			):
				frappe.throw(
					_("Member {0} has an Effective From after its Effective To.").format(member.technician),
					frappe.ValidationError,
				)

	def _validate_leader(self):
		if not self.team_leader:
			return
		active_members = {m.technician for m in self.members if m.active and m.technician}
		if self.team_leader not in active_members:
			frappe.throw(
				_("The team leader must be an active member of the team."),
				frappe.ValidationError,
			)

	def _validate_no_overlapping_membership(self):
		"""A technician may not be an active member of two teams at the same time."""
		for member in self.members:
			if not (member.active and member.technician):
				continue
			others = frappe.get_all(
				"Service Team Member",
				filters={
					"parenttype": "Service Team",
					"technician": member.technician,
					"active": 1,
					"parent": ["!=", self.name or ""],
				},
				fields=["parent", "effective_from", "effective_to"],
			)
			for other in others:
				if _windows_overlap(
					member.effective_from, member.effective_to, other.effective_from, other.effective_to
				):
					frappe.throw(
						_("{0} is already an active member of team {1} during an overlapping period.").format(
							member.technician, other.parent
						),
						frappe.ValidationError,
					)


def _technician_company_map(technicians: list[str]) -> dict[str, str]:
	if not technicians:
		return {}
	rows = frappe.get_all(
		"Technician",
		filters={"name": ["in", list(set(technicians))]},
		fields=["name", "company"],
	)
	return {row.name: row.company for row in rows}


def _windows_overlap(from1, to1, from2, to2) -> bool:
	"""Two open-ended date windows overlap. A missing bound is treated as unbounded."""
	from1 = getdate(from1) if from1 else None
	to1 = getdate(to1) if to1 else None
	from2 = getdate(from2) if from2 else None
	to2 = getdate(to2) if to2 else None
	if from1 and to2 and from1 > to2:
		return False
	if from2 and to1 and from2 > to1:
		return False
	return True
