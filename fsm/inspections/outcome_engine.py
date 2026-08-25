from __future__ import annotations

from dataclasses import dataclass

from frappe.utils import cint, flt, getdate


@dataclass
class InspectionOutcome:
	overall_result: str
	corrective_action_hint: str
	valid: bool
	errors: list[str]


def evaluate_inspection(inspection) -> InspectionOutcome:
	errors = []
	failures = []
	for row in inspection.results:
		passed, message = _evaluate_row(row)
		row.passed = int(passed)
		row.validation_message = message or ""
		if message:
			errors.append(f"{row.item_code}: {message}")
		elif not passed:
			failures.append(row)

	if errors:
		return InspectionOutcome("Pending", "", False, errors)
	if not failures:
		return InspectionOutcome("Pass", "", True, [])

	actions = {row.action_hint for row in failures if row.action_hint and row.action_hint != "None"}
	severity = {row.failure_severity for row in failures}
	if "Stop Work" in actions or "Critical" in severity:
		overall = "Fail"
	elif "Replace" in actions:
		overall = "Needs Replacement"
	elif "Repair" in actions:
		overall = "Needs Repair"
	elif "Refill" in actions:
		overall = "Needs Refill"
	else:
		overall = "Fail"
	hint = ", ".join(sorted(actions)) if actions else "Review failed inspection items"
	return InspectionOutcome(overall, hint, True, [])


def _evaluate_row(row):
	if not cint(row.responded):
		return (not cint(row.required), "Response is required" if cint(row.required) else "")
	if cint(row.evidence_required) and not (row.evidence or row.attachment or row.signature):
		return False, "Required evidence is missing"

	type_ = row.response_type
	value = (row.response_value or "").strip()
	if type_ == "Yes/No":
		if value.lower() not in {"yes", "no", "1", "0", "true", "false"}:
			return False, "Enter Yes or No"
		return value.lower() in {"yes", "1", "true"}, ""
	if type_ == "Pass/Fail":
		if value.lower() not in {"pass", "fail"}:
			return False, "Enter Pass or Fail"
		return value.lower() == "pass", ""
	if type_ in {"Number", "Measurement"}:
		value = flt(row.numeric_value)
		if row.min_value is not None and value < flt(row.min_value):
			return False, ""
		if row.max_value is not None and value > flt(row.max_value):
			return False, ""
		return True, ""
	if type_ == "Select":
		options = {option.strip() for option in (row.options or "").splitlines() if option.strip()}
		return (value in options, "" if value in options else "Select an allowed option")
	if type_ == "Date":
		if not row.date_value:
			return False, "Enter a valid date"
		try:
			getdate(row.date_value)
		except Exception:
			return False, "Enter a valid date"
		return True, ""
	if type_ == "Photo":
		return (bool(row.attachment), "" if row.attachment else "Photo is required")
	if type_ == "Signature":
		return (bool(row.signature), "" if row.signature else "Signature is required")
	if type_ == "Text":
		return (
			bool(value) or not cint(row.required),
			"" if value or not cint(row.required) else "Text is required",
		)
	return False, "Unsupported response type"
