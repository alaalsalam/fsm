# ADR-005: Separate Request, Job, and Visit responsibilities

- Status: Accepted and implemented for the CORE slice
- Date: 2026-08-24

## Context

Intake, the service commitment, and physical attendance have different cardinality and state. Treating them as one document prevents follow-up visits; treating them as three competing work orders duplicates truth.

## Decision

- **Service Request** owns intake, triage, consent, rejection, and one-way conversion.
- **Service Job** owns the service commitment and overall operational outcome.
- **Service Visit** owns one attendance attempt, crew, check-in/out, execution evidence, and outcome.

The implemented CORE cardinalities are `Service Request 1:N Service Job` and `Service Job 1:N Service Visit`; the future Job Equipment relation remains design-only. A Request may be fulfilled by multiple Jobs when triage produces separate commitments; each Job retains its Request origin and has zero or more Visits. A Visit cannot invoice, post stock, or close a Job. `Service Appointment` was migrated in place to Service Request; a duplicate runtime DocType does not coexist.

## Consequences

- Follow-up/no-access visits do not create duplicate Jobs.
- Customer booking status is not confused with Job execution state.
- Job completion is guarded by required Visit outcomes.

## Implementation record

The guarded rename patch, Request/Job/Visit command service, append-only Event Log, and authorization tests were delivered and verified by CORE-CLOSEOUT.
