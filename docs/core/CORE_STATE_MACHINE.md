# CORE state machines

All transitions are defined in `fsm/service_operations/state.py`, authorized in command handlers, saved with the internal `fsm_command` flag, and followed by an immutable event.

## Service Request

```text
Draft ──> Open ──> Triaged ──> Converted ──> Closed
  └────────┴──────────┴────────────┴────────> Cancelled
                 Open/Triaged ──────────────> Closed
```

Exact transitions: Draft→Open/Cancelled; Open→Triaged/Converted/Closed/Cancelled; Triaged→Converted/Closed/Cancelled; Converted→Closed/Cancelled. Closed and Cancelled are terminal.

## Service Job

```text
Draft → Planned → Scheduled → Dispatched → In Progress → Completed
                    │            │             │
                    └────────────┴────────────> On Hold ──> prior active state
Any non-terminal state ──────────────────────> Cancelled
```

Scheduled may enter In Progress from an eligible Visit projection. On Hold resumes to its recorded Scheduled, Dispatched, or In Progress state. Completion requires no active Visit and the configured checklist/evidence policy. Completed and Cancelled are terminal.

Job phase is separate from status: Planning, Travel, Check-In, Inspection, Diagnosis, On-Site Service, Workshop, Testing, Customer Verification, Closeout. Visit execution may project phase and may start an eligible Job, but it never completes it.

## Service Visit

```text
Planned → Dispatched → En Route → Checked In → In Progress → Checked Out → Completed
   └──────────┴───────────┴────────────┴─────────────┴────────────┴──────> Cancelled
```

Completed and Cancelled are terminal. Only the assigned technician, an in-scope FSM Manager, or System Manager may execute applicable commands.

## Prohibited behavior

- Direct lifecycle field writes through generic resource APIs.
- Visit→Request writes or controller save chains.
- Checklist-driven implicit Job completion.
- Visit completion implying Job completion.
- Reopening terminal records without a future, separately approved audited command.
