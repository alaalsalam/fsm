import frappe

from fsm.maintenance.engine import generate_occurrences, release_occurrences, update_occurrence_statuses


def run_daily_maintenance():
	"""Idempotent daily PM generation, status projection, and eligible Job release."""
	for plan in frappe.get_all("Maintenance Plan", filters={"status": "Active"}, pluck="name", limit=10000):
		generate_occurrences(plan)
	update_occurrence_statuses()
	return release_occurrences()
