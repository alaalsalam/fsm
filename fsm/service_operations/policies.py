import frappe
from frappe import _


class CompletionPolicy:
	"""Canonical completion gate shared by Console, Mobile and APIs."""

	def validate(self, job) -> None:
		from fsm.process.completion import completion_blockers

		blockers = completion_blockers(job)
		if blockers:
			frappe.throw(
				_("The Service Job cannot be completed: {0}").format(
					"; ".join(row["message"] for row in blockers)
				),
				frappe.ValidationError,
			)


def validate_coordinates(latitude=None, longitude=None, accuracy=None) -> None:
	if latitude in (None, "") and longitude in (None, ""):
		return
	try:
		lat, lon = float(latitude), float(longitude)
	except TypeError, ValueError:
		frappe.throw(_("Latitude and longitude must be numeric."))
	if not -90 <= lat <= 90 or not -180 <= lon <= 180:
		frappe.throw(_("Coordinates are outside valid bounds."))
	if accuracy not in (None, "") and float(accuracy) < 0:
		frappe.throw(_("GPS accuracy cannot be negative."))
