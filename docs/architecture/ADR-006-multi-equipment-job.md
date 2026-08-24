# ADR-006: A Service Job supports multiple equipment items

- Status: Proposed
- Date: 2026-08-24

## Context

A single customer visit may service several units. One-Job-per-unit fragments scheduling, labour, travel, communication, and billing; a single header equipment link cannot express per-unit outcomes.

## Decision

Introduce, only after approval, a Job Equipment child relation under Service Job. Each row links ERPNext Item and optionally Serial No and Asset, records the requested service/outcome, and may reference equipment-scoped checklist results. ERPNext remains equipment master and warranty source.

At least one row is required for equipment-centric Jobs; non-equipment services may explicitly opt out by Job type. Duplicate Serial No rows in one active Job are rejected unless the service policy permits distinct operations.

## Consequences

- Job remains the shared visit/travel/commercial correlation.
- Outcomes and checklists can be evaluated per unit.
- There is no FSM Installed Base master.

## Approval gate

Field mapping to ERPNext Serial No/Asset and migration of existing single-equipment assumptions must be approved before schema creation.
