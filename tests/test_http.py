import pytest

from monitor_watch.http import FetchError, validate_payload


def test_html_content_type_is_accepted() -> None:
    assert validate_payload(b"<html></html>", "text/html; charset=utf-8", 100) == "<html></html>"


def test_non_html_content_type_is_rejected() -> None:
    with pytest.raises(FetchError, match="unsupported content type") as error:
        validate_payload(b"{}", "application/json", 100)
    assert error.value.code == "invalid_content_type"


def test_oversized_response_is_rejected() -> None:
    with pytest.raises(FetchError, match="exceeded") as error:
        validate_payload(b"x" * 11, "text/html", 10)
    assert error.value.code == "response_too_large"
