# Incident runbook

## Collector or policy incidents

- Parser failure: do not retry repeatedly. Save a sanitized bounded response as a test
  fixture, compare structured fields, patch offline, run validation, then one smoke.
- Robots/terms change: disable the collector immediately, record the new source and
  review date, and resume only after explicit approval.
- CAPTCHA/WAF: stop. Do not add browser automation, rotate identities or bypass it.
- Incorrect price/model: disable the URL or collector, retain the rejected observation,
  narrow exact-model/price parsing, add a regression fixture and rebuild current data.
- Unexpected marketplace seller: treat as rejected, disable if seller identity cannot
  be established, and add the exact malicious/ambiguous case to tests.

## Output and GitHub incidents

- Dashboard build failure: validate JSON schemas, rebuild twice, compare hashes and
  inspect browser console. Deploy only the last validated `docs/` tree.
- Duplicate alert: close the newer issue, confirm its hidden deduplication marker and
  price-band key, add the issue body to a mocked regression test. Do not update existing
  issues unless that separate flag is approved.
- Actions failure: inspect the short-lived artifact, action SHA, lockfile and collector
  health. Never paste tokens or full personalized HTML into logs/issues.
- Rollback: disable all automation flags, disable the affected collector, use `git revert`
  for the relevant code/data commit, rerun validation and manually verify the dashboard.
  Do not force-push or delete historical evidence.
