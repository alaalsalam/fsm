# Typed Inspection Engine

Date: 2026-08-25. Domain owner: **FSM Inspections**. This engine complements the simple Job checklist; it does not replace checklist task progress or embed equipment responses in Service Job.

## Model

| Entity | Kind | Responsibility |
|---|---|---|
| Inspection Template | Versioned root | Company/category-scoped typed inspection definition and lifecycle. |
| Inspection Template Item | Child | Code, label, response type, required/threshold/options/evidence/severity/action rules. |
| Equipment Inspection | Durable root | One execution against one Installed Equipment within one Service Job and optional Visit. |
| Equipment Inspection Result | Child | Snapshot of each template rule plus response, evidence and server-calculated outcome. |

Supported response types are Yes/No, Pass/Fail, Number, Text, Select, Date, Photo, Signature and Measurement. Multiple inspections may exist for each Job Equipment row; responses are never flattened into Service Job.

## Invariants

- Template item codes are unique and select options/measurement ranges are validated.
- Template revisions increment when the typed definition changes; an Inspection snapshots the revision and rules.
- Inspection equipment must be present in the canonical Job's equipment table and share Customer/Company.
- An optional Visit must belong to the same Job.
- Assigned Technicians may execute only their Jobs; Managers remain Company-scoped; Customers are read-only owners.
- Direct create, result mutation, outcome mutation and delete are blocked. Commands are the only write surface.
- The frontend cannot submit `passed`, severity, action hint or overall result.
