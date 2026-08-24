from __future__ import annotations

import frappe
from frappe import _


REQUEST_TRANSITIONS = {
	"Draft": {"Open", "Cancelled"},
	"Open": {"Triaged", "Converted", "Closed", "Cancelled"},
	"Triaged": {"Converted", "Closed", "Cancelled"},
	"Converted": {"Closed", "Cancelled"},
	"Closed": set(),
	"Cancelled": set(),
}

JOB_TRANSITIONS = {
	"Draft": {"Planned", "Cancelled"},
	"Planned": {"Scheduled", "Cancelled"},
	"Scheduled": {"Dispatched", "In Progress", "On Hold", "Cancelled"},
	"Dispatched": {"In Progress", "On Hold", "Cancelled"},
	"In Progress": {"On Hold", "Completed", "Cancelled"},
	"On Hold": {"Scheduled", "Dispatched", "In Progress", "Cancelled"},
	"Completed": set(),
	"Cancelled": set(),
}

VISIT_TRANSITIONS = {
	"Planned": {"Dispatched", "Cancelled"},
	"Dispatched": {"En Route", "Cancelled"},
	"En Route": {"Checked In", "Cancelled"},
	"Checked In": {"In Progress", "Cancelled"},
	"In Progress": {"Checked Out", "Cancelled"},
	"Checked Out": {"Completed", "Cancelled"},
	"Completed": set(),
	"Cancelled": set(),
}


def assert_transition(machine: dict[str, set[str]], current: str, target: str, label: str) -> None:
	if target not in machine.get(current, set()):
		frappe.throw(
			_("Illegal {0} transition from {1} to {2}.").format(label, current, target),
			frappe.ValidationError,
		)


def transition(doc, target: str, machine: dict[str, set[str]], label: str, **values):
	assert_transition(machine, doc.status, target, label)
	doc.flags.fsm_command = True
	doc.status = target
	for field, value in values.items():
		setattr(doc, field, value)
	doc.save()
	return doc
