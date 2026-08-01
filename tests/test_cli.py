import sys

import pytest

from monitor_watch import cli
from monitor_watch.http import FetchError


def test_smoke_parser_failure_reports_structured_health(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_fetch(*args: object, **kwargs: object) -> str:
        raise FetchError("invalid_content_type", "fixture rejection")

    monkeypatch.setattr(cli, "fetch_html", fail_fetch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["monitor-watch", "smoke", "--retailer", "umart", "--model", "U3225QE"],
    )
    assert cli.main() == 1
    captured = capsys.readouterr()
    assert '"status": "failed"' in captured.err
    assert '"error_code": "invalid_content_type"' in captured.err
    assert "LIVE NETWORK ACTIVITY" in captured.err
