# monitor-watch-au

An auditable Australian price, stock, warranty and strict-specification tracker for
31.5–32-inch 4K monitors. GitHub Actions provides bounded daily execution without an
always-on home computer; normalized JSON remains reviewable in Git, while the dashboard
is static HTML/CSS/JavaScript suitable for GitHub Pages.

## Active shortlist

1. LG UltraGear 32GR93U-B
2. LG UltraGear 32G810SA-W
3. Dell G3223Q
4. Dell UltraSharp U3225QE
5. ASUS ROG Strix XG32UCG

Umart and PLE are enabled after documented robots/terms review. LG Australia, Computer
Alliance, Centre Com, Dell Australia and Scorptec are disabled. OLED, VA, curved,
refurbished, used, factory-second, grey-import, ambiguous and marketplace offers cannot
qualify.

## Architecture

YAML configuration defines models, retailer pages, thresholds and automation gates.
Collectors make bounded static requests and emit typed observations with field-level
evidence. Qualification is conservative, monthly JSON storage deduplicates each
retailer/model/UTC day, scoring uses only cited facts, and `docs/` renders committed
JSON without a build server. Validation, collection, publication and alerts have
separate workflows and permissions.

## Local setup and commands

```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install uv
.venv\Scripts\uv sync --locked --all-extras
.venv\Scripts\python -m monitor_watch.cli validate
.venv\Scripts\python -m monitor_watch.cli dashboard
.venv\Scripts\python -m monitor_watch.cli check-retailer-reviews
.venv\Scripts\python -m monitor_watch.cli evaluate-alerts --dry-run
```

Live access is always explicit and writes nothing without `--write`:

```powershell
.venv\Scripts\python -m monitor_watch.cli smoke --retailer ple --model 32GR93U-B
.venv\Scripts\python -m monitor_watch.cli collect --retailer umart --model U3225QE
.venv\Scripts\python -m monitor_watch.cli collect-all
.venv\Scripts\python -m monitor_watch.cli explain --retailer Umart --model "Dell UltraSharp U3225QE"
```

To add a model, add one exact canonical entry and narrowly approved aliases to
`config/monitors.yaml`, add a threshold record, then add cited specification evidence.
To add a retailer, first document robots, terms, permitted paths, method and review due
date under `docs/retailers/`; only then add a fixture-tested collector and configured
URLs. Never infer a model, permission, warranty or seller relationship.

## Qualification, scoring and thresholds

Qualification requires an exact model, new condition, available stock, Australian
stock, approved retailer/direct manufacturer, known seller, non-marketplace and
non-grey-import status, adequate evidenced warranty, known delivered price, mandatory
field evidence, and an approved buy threshold. Unknown values reject. Thresholds remain
visible while provisional, but `approved: true` also requires `approved_at` and
`approved_by`; no CLI or workflow bypass exists.

Scores use weights 30 productivity, 20 panel/image quality, 15 connectivity, 10 gaming,
10 warranty/support and 15 value. Rules derive only from cited factual inputs. Unknown
components are omitted and lower confidence rather than scoring zero. This is not a
substitute for subjective review testing.

## Automation modes

Mode A is the default: collection writes only inside its runner and uploads normalized
data, a patch and short-lived diagnostics for operator review. The operator may repeat
locally with `--write`, rebuild, inspect and commit.

Mode B is implemented but disabled: `commit_observations: true` activates a separate
`contents: write` job, skips unchanged data, and attributes a `[skip ci]` data commit to
GitHub Actions. Alert and Pages flags are independent and false. Enabling any write
requires a separate approval and repository configuration review.

## GitHub and Pages

Create the repository only after reviewing this tree, set `main`, retain restricted
default workflow permissions, and enable Pages with GitHub Actions as its source only
after `publish_dashboard` is approved. Private-repository Pages availability depends on
the GitHub plan. See `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md` and `docs/RUNBOOK.md`.

## Limitations and ethics

Retailer markup, robots and terms drift; reviews expire and collection then fails
closed. Delivery and warranty are frequently absent. No browser automation, bot bypass,
paid API, purchase action or credential is included. Requests are identifiable,
time-bounded, size-capped and minimally retried. Disable a collector immediately if its
policy or access behavior changes. Roll back data/code with a normal revert after
preserving diagnostic evidence; never rewrite shared history.
