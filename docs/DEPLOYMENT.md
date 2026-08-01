# Deployment checklist

1. Create a GitHub repository only after local review; public improves Pages availability
   and transparency, while private protects history but may require a paid Pages plan.
2. Push an intentionally reviewed initial commit to `main`; configure it as default and
   protect it with the Validate check.
3. Set default Actions workflow permissions to read-only. Allow Actions to create/approve
   PRs only if a later design explicitly needs it (this repository does not).
4. Create the `github-pages` environment and optionally add required reviewers.
5. In Pages settings choose **GitHub Actions** as source. Do not enable until the static
   output and repository visibility are approved.
6. Leave every `config/automation.yaml` flag false for the first manual dispatch.
7. Dispatch Validate, inspect it, then dispatch Collect and download its artifact. Confirm
   no commit, issue or deployment occurred.
8. Review normalized observations locally, rebuild twice and inspect the dashboard.
9. To publish, separately approve `publish_dashboard: true`, enable Pages and dispatch its
   workflow. To enable schedules, approve leaving the declared collection cron active.
10. Mode B additionally requires approving `commit_observations: true` and the conditional
    job's `contents: write`. Alerting additionally requires approved thresholds and
    `create_price_alerts: true`; the isolated job receives `issues: write` only.

After deployment verify the Pages URL, workflow permissions, artifact retention, alert
dry run, collector review dates and absence of unexpected commits/issues. Roll back using
the procedure in `RUNBOOK.md`.
