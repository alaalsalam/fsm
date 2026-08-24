# ADR-005: Separate Request, Job, and Visit responsibilities

- Status: Proposed
- Date: 2026-08-24

## Context

Intake, the service commitment, and physical attendance have different cardinality and state. Treating them as one document prevents follow-up visits; treating them as three competing work orders duplicates truth.

## Decision

- **Service Request** owns intake, triage, consent, rejection, and one-way conversion.
- **Service Job** owns the service commitment and overall operational outcome.
- **Service Visit** owns one attendance attempt, crew, check-in/out, execution evidence, and outcome.

A Request converts to at most one Job. A Job has zero or more Visits. A Visit cannot invoice, post stock, or close a different Job. The current `Service Appointment` must evolve through a controlled rename/migration or be explicitly adopted as Request; a duplicate Request DocType may not coexist.

## Consequences

- Follow-up/no-access visits do not create duplicate Jobs.
- Customer booking status is not confused with Job execution state.
- Job completion is guarded by required Visit outcomes.

## Approval gate

Approve the physical migration choice for `Service Appointment` before creating any Request/Visit schema.
