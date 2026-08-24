# ADR-008: Command authorization and least privilege

- Status: Accepted
- Date: 2026-08-24

## Context

DocType role metadata alone cannot express assigned-job, customer, company, and territory scope. The security gate found unrestricted reads and HTTP-reachable permission bypasses that required one enforceable backend policy.

## Decision

Authorization is default-deny and implemented in `fsm.security`:

1. `require_authenticated` establishes a non-Guest actor unless the endpoint is explicitly public.
2. `require_role` authorizes the command class; System Manager elevation is explicit, never inferred from UI visibility.
3. permission query hooks and `has_permission` hooks apply row scope to Service Request, Service Job, Service Visit, Service Event Log, Return, Message, Feedback, Time Log, Field Note, and Location Log.
4. `require_company_scope`, `require_manager_scope`, `require_customer_ownership`, and `require_technician_assignment` assert root-resource scope before reads, writes, or transitions.
5. `require_doc_read`/`require_doc_write`, field allowlists, bounded limits, and controller state guards constrain documents, payloads, and transitions.
6. `ignore_permissions=True` is permitted only for an enumerated guest bootstrap, authorized internal root operation, setup hook, or scheduler operation recorded in `IGNORE_PERMISSIONS_REGISTER.md`.

Technicians can read and mutate only their assigned Jobs/Visits and append authorized execution evidence. Customers can read only their own Requests, Jobs, messages, and feedback. FSM Managers are restricted by Company User Permission and optional territory scope. System Managers retain explicit global administration. Guest registration and Request intake have fixed payloads and rate limits; role and user type cannot be supplied by callers.

## Consequences

- `get_all` is forbidden for user-scoped reads unless root IDs are already scoped or a documented system/administrative guard precedes it.
- Negative tests cover company, technician, customer, Guest, dashboard, registration rollback, and direct child-document bypass.
- Bypass calls without a documented root guard fail review.
- Location and financial fields receive field-level response shaping.

## Approval gate

Satisfied by GATE-001 backend security tests and the API/data/ignore-permissions matrices. Future APIs must update those matrices and add positive and negative tests in the same commit.
