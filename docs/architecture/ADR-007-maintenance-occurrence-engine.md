# ADR-007: Deterministic maintenance occurrence engine

- Status: Proposed
- Date: 2026-08-24

## Context

Recurring maintenance must survive scheduler retries, timezone/DST boundaries, plan changes, pauses, and missed periods without generating duplicate Jobs. ERPNext maintenance capabilities must be reviewed before adding FSM schema.

## Decision

If the ERPNext overlap review confirms a domain gap, separate recurrence definition from execution:

- Maintenance Plan owns rule, timezone, start/end, equipment, service template, and generation lead time.
- Maintenance Occurrence is a unique ledger row for `(plan, due_at)` with Pending/Generated/Skipped/Superseded/Failed state.
- Generation uses an idempotency key and creates at most one Request or Job according to policy.
- Occurrence never becomes the execution record; its generated Service Job remains canonical.

Plan edits do not rewrite completed/generated occurrences. Future pending occurrences are superseded and recalculated with audit history.

## Consequences

- Scheduler retries are safe.
- Catch-up/skip policies are explicit.
- Timezone and DST are part of the contract.
- No DocType is authorized until ERPNext Maintenance Schedule/Visit overlap is documented and this ADR is accepted.

## Approval gate

Approve recurrence grammar, lead/catch-up policy, uniqueness constraint, timezone rules, and ERPNext overlap decision.
