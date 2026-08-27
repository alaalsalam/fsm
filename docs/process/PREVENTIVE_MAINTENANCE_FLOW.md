# Preventive maintenance flow

`Contract/manual Plan → Occurrences → grouped release → one Job with many equipment → Team → Visit → Inspections/outcomes → materials/workshop when required → Report/Certificate policy → Job completion → Occurrence completion → next due/history`.

Occurrence identity and release keys make scheduler retries idempotent. Contract-to-plan generation is preview-first, creates one draft plan per covered site and reuses a non-cancelled existing plan.
