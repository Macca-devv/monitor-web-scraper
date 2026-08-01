# Threat model

Retailer content is untrusted even when delivered over HTTPS. A compromised page could
inject HTML, Markdown, formulas, huge bodies, redirects or misleading seller/model data.
Collectors parse data, never execute it; HTTP limits type, bytes, timeout and retries.
Exact models and evidence are validated. Dashboard strings use DOM `textContent`; issue
strings are line-flattened and HTML-escaped. JSON is used instead of CSV; any future CSV
export must prefix formula-leading cells. Redirect destinations remain a maintenance risk
and must stay on the configured retailer origin.

Dependencies or Actions may be compromised. Python is lockfile-pinned, Actions use full
commit SHAs, Dependabot proposes reviewable updates without auto-merge, and validation
runs no live collection. Scraped values never enter shell interpolation, workflow
commands, `eval`, or executable source.

Token misuse is constrained by separate workflows: normal validation/collection has
`contents: read`; Pages alone has Pages/OIDC writes; a skipped alert job alone has issue
write; automated commits are a separately skipped job. Credentials are not stored and
checkout persistence is disabled except in the explicitly enabled push job.

Denial of service is bounded by response/job timeouts, one page request, concurrency and
retention. Raw HTML is not committed. Legal permission can drift independently of
robots; dated reviews expire and fail closed. A CAPTCHA, WAF or new restrictive term
causes disablement rather than circumvention.
