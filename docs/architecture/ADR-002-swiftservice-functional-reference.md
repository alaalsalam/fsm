# ADR-002: SwiftService is a functional reference only

- Status: Accepted
- Date: 2026-08-24

## Context

SwiftService demonstrates a broad service lifecycle but contains 79 DocTypes, duplicated ERPNext commercial/stock concepts, a monolithic API, no tests, and many permission bypasses.

## Decision

Review SwiftService at capability level. Each capability is classified as Implemented, Partial, Schema/UI only, Documentation only, Not suitable, Duplicate of ERPNext, or Candidate for clean-room implementation. Implementation detail is neither authoritative nor reusable.

## Consequences

- Workflow ideas may shape requirements and tests.
- SwiftService names do not dictate DIGIT DocTypes or routes.
- “Implemented” describes reference evidence, not fitness for adoption.
- The parity register is complete enough to prevent silent scope adoption.

## Approval gate

Any future parity story must cite its register row, target aggregate, ERPNext overlap analysis, and clean-room acceptance test.
