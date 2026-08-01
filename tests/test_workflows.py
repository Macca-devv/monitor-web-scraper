import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _load(name: str) -> dict[str, object]:
    text = (WORKFLOWS / name).read_text(encoding="utf-8").replace("\non:\n", '\n"on":\n', 1)
    value = yaml.safe_load(text)
    assert isinstance(value, dict)
    return value


def test_automation_defaults_are_read_only() -> None:
    automation = yaml.safe_load((ROOT / "config/automation.yaml").read_text(encoding="utf-8"))[
        "automation"
    ]
    assert automation["commit_observations"] is False
    assert automation["create_price_alerts"] is False
    assert automation["publish_dashboard"] is False


def test_workflow_permissions_and_concurrency() -> None:
    validate = _load("validate.yml")
    collect = _load("collect.yml")
    pages = _load("pages.yml")
    alerts = _load("price-alert.yml")
    assert validate["permissions"] == {"contents": "read"}
    assert collect["permissions"] == {"contents": "read"}
    assert pages["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    assert alerts["permissions"] == {"contents": "read"}
    assert "concurrency" in collect and "concurrency" in pages


def test_validate_never_scrapes_and_collection_cannot_recurse() -> None:
    validate_text = (WORKFLOWS / "validate.yml").read_text(encoding="utf-8")
    collect = _load("collect.yml")
    assert "collect-all" not in validate_text and " smoke " not in validate_text
    assert "pull_request_target" not in validate_text
    triggers = collect["on"]
    assert isinstance(triggers, dict)
    assert "push" not in triggers and "pull_request" not in triggers


def test_every_action_is_pinned_to_a_full_sha() -> None:
    for path in WORKFLOWS.glob("*.yml"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "uses:" in line:
                reference = line.split("uses:", 1)[1].split("#", 1)[0].strip()
                assert re.search(r"@[0-9a-f]{40}$", reference), (path, reference)


def test_no_unsafe_workflow_features() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOWS.glob("*.yml"))
    assert "pull_request_target" not in combined
    assert "eval " not in combined
    assert "::set-output" not in combined
