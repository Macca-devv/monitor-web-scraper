import socket

import pytest


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("unit tests must not access the network")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
