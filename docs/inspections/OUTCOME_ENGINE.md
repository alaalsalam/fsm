# Inspection outcome engine

`fsm.inspections.outcome_engine.evaluate_inspection` is the sole outcome authority.

- Missing mandatory responses, invalid enumerations/dates and required evidence block completion.
- Yes/No and Pass/Fail are normalized server-side.
- Number/Measurement responses compare against snapshotted minimum/maximum thresholds.
- Photo and Signature types require their corresponding evidence field.
- Valid failed rows retain severity and configured action hint.
- Critical or Stop Work failures produce `Fail`; Replace, Repair and Refill map to `Needs Replacement`, `Needs Repair` and `Needs Refill` respectively.
- A clean inspection produces `Pass`.
- `Not Accessible` and `Skipped` require an explicit reason through a separate guarded command.

This phase produces corrective-action hints only. Failure Analysis and workshop/material side effects belong to later gated domains and are not created silently.
