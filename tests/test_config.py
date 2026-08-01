from pathlib import Path

from monitor_watch.config import load_monitors


def test_shortlist_has_five_enabled_exact_entries() -> None:
    monitors = load_monitors(Path("config/monitors.yaml"))
    assert len(monitors) == 5
    assert all(item.enabled and not item.placeholder and item.model_number for item in monitors)


def test_asus_replaces_unconfirmed_miniled_placeholder() -> None:
    monitors = load_monitors(Path("config/monitors.yaml"))
    assert any(item.canonical_model == "ASUS ROG Strix XG32UCG" for item in monitors)
    assert all("UNCONFIRMED" not in item.canonical_model for item in monitors)
