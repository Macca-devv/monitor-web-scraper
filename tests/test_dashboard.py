import hashlib
import json
from pathlib import Path

from monitor_watch.dashboard import build_dashboard


def test_dashboard_contains_five_models_and_uses_safe_dom_rendering() -> None:
    root = Path(__file__).parents[1]
    output = build_dashboard(root)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert len(data["models"]) == 5
    script = (root / "docs/app.js").read_text(encoding="utf-8")
    assert ".textContent" in script
    assert "innerHTML" not in script


def test_pages_output_is_deterministic() -> None:
    root = Path(__file__).parents[1]
    first = hashlib.sha256(build_dashboard(root).read_bytes()).digest()
    second = hashlib.sha256(build_dashboard(root).read_bytes()).digest()
    assert first == second
