# Operations

## Daily operation

The collection workflow runs at 16:17 UTC and may also be dispatched manually. With
the initial flags it collects only enabled/currently reviewed retailers, validates the
normalized observations, rebuilds dashboard data and uploads a 14-day review artifact.
It neither commits nor alerts. Download the artifact, inspect `collection-output.log`,
the normalized JSON and patch, then reproduce locally with an explicit `--write` before
committing reviewed data.

Run `check-retailer-reviews` before any smoke. A successful collector health row means
the page was fetched and parsed, not that an offer qualified. Failed means transport,
content or parser failure. No row means no completed collection. Out-of-stock and
unknown-evidence offers are expected rejected observations.

## Controlled operations

- Smoke one page: `python -m monitor_watch.cli smoke --retailer ple --model 32GR93U-B`.
- Validate: `python -m monitor_watch.cli validate`.
- Rebuild: `python -m monitor_watch.cli dashboard`.
- Explain current data: use `explain` with retailer and canonical model.
- Preview alerts: `python -m monitor_watch.cli evaluate-alerts --dry-run`.

Approve a threshold only after documenting who approved it and when. Set `approved`,
`approved_at`, and `approved_by` together; validate and review the dry run. Enabling
`create_price_alerts` is a separate approval. Existing open issues are matched by a
model/retailer/AUD 25 band marker.

Review each retailer's robots and terms on or before `review_due`, update its evidence
document and configuration date, then rerun fixture and smoke tests. An overdue enabled
collector is refused. A CAPTCHA/WAF or new prohibition requires immediate disablement,
not a grace period. Schedule re-enablement means restoring an approved current review
and manually dispatching once before relying on the declared cron trigger.

History uses compact monthly JSON, one retailer/model/day, with 24-month pruning. At
five monitors × four retailers × 365 days, the ceiling is 7,300 observations/year.
At an estimated 1.5–2.5 KB normalized record, expect roughly 11–18 MB/year and 22–36 MB
at steady-state retention. Only normalized records enter Git; raw diagnostic responses,
if temporarily needed, belong in short-lived Actions artifacts and must be sanitized.
