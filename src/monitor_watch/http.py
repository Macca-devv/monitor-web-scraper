"""Small bounded HTTP transport for explicitly invoked live collection."""

from dataclasses import dataclass
from time import sleep

import httpx


class FetchError(RuntimeError):
    """A safe, classified collection failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class FetchPolicy:
    user_agent: str
    timeout_seconds: float
    maximum_bytes: int
    maximum_transient_retries: int = 1


def validate_payload(content: bytes, content_type: str, maximum_bytes: int) -> str:
    media_type = content_type.partition(";")[0].strip().casefold()
    if media_type not in {"text/html", "application/xhtml+xml"}:
        raise FetchError("invalid_content_type", f"unsupported content type: {content_type!r}")
    if len(content) > maximum_bytes:
        raise FetchError("response_too_large", f"response exceeded {maximum_bytes} bytes")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FetchError("invalid_encoding", "response was not valid UTF-8") from exc


def fetch_html(url: str, policy: FetchPolicy) -> str:
    headers = {"User-Agent": policy.user_agent, "Accept": "text/html,application/xhtml+xml"}
    attempts = policy.maximum_transient_retries + 1
    try:
        with httpx.Client(
            timeout=policy.timeout_seconds,
            follow_redirects=True,
            headers=headers,
        ) as client:
            for attempt in range(attempts):
                with client.stream("GET", url) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt + 1 < attempts:
                            sleep(min(2**attempt, 2))
                            continue
                        raise FetchError("transient_http_error", f"HTTP {response.status_code}")
                    if response.status_code >= 400:
                        raise FetchError("http_error", f"HTTP {response.status_code}")
                    content_type = response.headers.get("content-type", "")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > policy.maximum_bytes:
                            raise FetchError(
                                "response_too_large",
                                f"response exceeded {policy.maximum_bytes} bytes",
                            )
                        chunks.append(chunk)
                    return validate_payload(b"".join(chunks), content_type, policy.maximum_bytes)
    except httpx.HTTPError as exc:
        raise FetchError("network_error", f"network request failed: {type(exc).__name__}") from exc
    raise FetchError("internal_error", "request loop completed unexpectedly")
