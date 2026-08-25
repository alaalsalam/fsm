# PM scheduler and Job grouping

The daily hook calls `fsm.maintenance.tasks.run_daily_maintenance`. Its three ordered steps are generation, due/overdue projection, and release.

## Retry safety

1. Generation computes the durable occurrence identity before insert; a unique database field and duplicate recovery close concurrent retries.
2. Release locks all rows in a grouping bucket with `FOR UPDATE`.
3. The grouping key includes Plan revision, Company, Customer, Site, service type, configured due window and date bucket.
4. The Job release key is deterministic and unique. A concurrent duplicate insert resolves to the existing Job.
5. Occurrences are linked to the Job only after the Job exists and is moved through the canonical `plan_job` command.
6. A second scheduler run returns no duplicate Jobs or occurrences.

## Time policy

- Plan timezone is a validated IANA name.
- Local Frappe `Time` values are normalized before conversion.
- Non-existent DST times advance to the next valid local time.
- Ambiguous DST times honor first/second occurrence policy.
- Both computed UTC time and applied offset are persisted.

## Campaign grouping

Eligible occurrences are grouped into one Service Job with N `Service Job Equipment` rows. This supports large same-site campaigns without producing a Job per asset. Visits remain separately creatable under the existing `Service Job 1:N Service Visit` model when multiple attendances or crews are required.
