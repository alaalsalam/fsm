# ADR-008: Command authorization and least privilege

- Status: Proposed
- Date: 2026-08-24

## Context

Current metadata roles do not express assigned-job/customer scope, several APIs use unrestricted queries, and many writes bypass permissions.

## Decision

Use layered authorization:

1. Frappe authentication establishes actor identity.
2. Role policy authorizes the command class.
3. `frappe.has_permission(..., throw=True)` enforces DocType/document permission.
4. Domain scope asserts customer ownership, technician assignment, territory, or integration grant.
5. State guard validates the transition.
6. A narrowly scoped internal bypass is allowed only after steps 1–5 and is auditable.

Technicians see/modify assigned active work and append execution evidence; they cannot edit commercial truth or delete posted evidence. Customers see only their own requests/jobs/visits/messages/feedback. Managers see the operational organization. Integration credentials receive explicit scopes. Guest booking/registration is rate-limited and idempotent.

## Consequences

- `get_all` is forbidden for user-scoped reads unless an explicit privileged guard precedes it.
- Permission tests include positive and negative cases for every public/whitelisted command.
- Bypass calls without a documented guard fail review/CI.
- Location and financial fields receive field-level response shaping.

## Approval gate

The critical findings in `PERMISSION_AUDIT.md` and automated negative tests must close before external/mobile feature work.
