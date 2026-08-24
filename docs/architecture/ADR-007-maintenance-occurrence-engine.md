# ADR-007: Deterministic maintenance occurrence engine

- Status: Accepted
- Date: 2026-08-24

## Context

Recurring maintenance must survive scheduler retries, timezone/DST boundaries, plan changes, pauses, and missed periods without generating duplicate Jobs. ERPNext maintenance capabilities must be reviewed before adding FSM schema.

## Decision

If the ERPNext overlap review confirms a domain gap, separate recurrence definition from execution:

- Maintenance Plan owns rule, IANA timezone, start/end, equipment, service template, generation lead time, and an immutable revision number.
- Maintenance Occurrence is a unique ledger row for `(plan, plan_revision, due_at_utc)` with Pending/Generated/Skipped/Superseded/Failed state; the local due time and UTC offset are retained for audit.
- Generation uses the occurrence identity as an idempotency key and creates at most one Request or Job according to policy, including after retries or concurrent scheduler workers.
- Occurrence never becomes the execution record; its generated Service Job remains canonical.

Plan edits create a new plan revision and do not rewrite completed/generated occurrences. Future pending occurrences from the old revision are superseded and recalculated with audit history. DST gaps and folds are resolved by an explicit policy attached to the plan timezone.

## Consequences

- Scheduler retries are safe.
- Catch-up/skip policies are explicit.
- Timezone and DST are part of the contract.
- No DocType is authorized until ERPNext Maintenance Schedule/Visit overlap is documented and this ADR is accepted.

## Approval gate

Approve recurrence grammar, lead/catch-up policy, uniqueness constraint, timezone rules, and ERPNext overlap decision.
