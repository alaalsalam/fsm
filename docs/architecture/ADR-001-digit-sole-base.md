# ADR-001: DIGIT FSM is the sole application base

- Status: Accepted
- Date: 2026-08-24

## Context

Two repositories were supplied. Combining their schemas or source would create competing aggregates, uncertain provenance, and incompatible quality/security assumptions.

## Decision

DIGIT FSM is the only application codebase. SwiftService is a functional reference used solely to identify capabilities, workflows, and acceptance scenarios. No SwiftService code, schema, assets, generated output, or copied implementation text may enter the project. Accepted capabilities are independently designed against ERPNext v16 and implemented clean-room after this ADR set is approved.

## Consequences

- All commits, migrations, and releases originate from the FSM repository.
- The parity register is a decision log, not a porting backlog.
- A provenance review is required for each future parity implementation.
- GPL-3.0 reference code does not contaminate the MIT DIGIT base.

## Approval gate

Repository scans must show no SwiftService paths/content, and every parity item must name a target owner and decision.
