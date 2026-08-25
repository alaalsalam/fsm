# Failure Analysis / RCA model

`Failure Analysis` is a diagnostic record under the canonical Service Job. It does not schedule work, post
stock, or replace Equipment Inspection.

Lifecycle: Draft → Inspection → Analysis → Root Cause Identified → Corrective Action → Verification → Closed.
Any non-terminal state may be Cancelled where the transition map permits it; cancellation requires a reason.
Root cause, corrective action and verification are mandatory before their corresponding transitions.

The record must reference one Installed Equipment row on its Service Job. Optional Service Visit and Equipment
Inspection references must belong to the same Job/equipment context.

Repeat detection counts earlier non-cancelled analyses on the same Installed Equipment inside
`Service Settings.repeat_failure_window_days`. Safety risk, Critical severity, or the configured previous-failure
threshold marks the analysis escalated. The server calculates a priority suggestion. It never changes Service Job
priority automatically: a scoped Manager must apply the suggestion, which emits
`JobPriorityChangedFromFailureAnalysis`.
