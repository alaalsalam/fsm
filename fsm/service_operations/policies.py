import frappe
from frappe import _


class CompletionPolicy:
	"""Stable extension point for later inspection, signature, spares and commercial gates."""

	def validate(self, job) -> None:
		active = frappe.get_list(
			"Service Visit",
			filters={"service_job": job.name, "status": ["not in", ["Completed", "Cancelled"]]},
			pluck="name",
			limit=1,
		)
		if active:
			frappe.throw(_("Complete or cancel all active visits before completing the job."))
		if job.tasks and any(row.status != "Done" for row in job.tasks):
			frappe.throw(_("Finish the mandatory checklist before completing the job."))


def validate_coordinates(latitude=None, longitude=None, accuracy=None) -> None:
	if latitude in (None, "") and longitude in (None, ""):
		return
	try:
		lat, lon = float(latitude), float(longitude)
	except (TypeError, ValueError):
		frappe.throw(_("Latitude and longitude must be numeric."))
	if not -90 <= lat <= 90 or not -180 <= lon <= 180:
		frappe.throw(_("Coordinates are outside valid bounds."))
	if accuracy not in (None, "") and float(accuracy) < 0:
		frappe.throw(_("GPS accuracy cannot be negative."))
