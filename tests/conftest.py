import pytest

from notifier_app import create_app


@pytest.fixture
def environ():
    return {}


@pytest.fixture
def app(tmp_path, environ):
    return create_app({
        "TESTING": True,
        "CONFIG_PATH": str(tmp_path / "config.json"),
        "ENVIRON": environ,
    })


@pytest.fixture
def client(app):
    return app.test_client()


class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


@pytest.fixture
def fake_requests(monkeypatch):
    """Capture outgoing HTTP calls made by the notifier clients."""
    calls = []
    state = {"response": FakeResponse(200, {}), "error": None}

    def fake_request(method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        if state["error"] is not None:
            raise state["error"]
        return state["response"]

    monkeypatch.setattr("notifier_app.notifiers.base.requests.request", fake_request)

    def configure(status_code=200, body=None, error=None):
        state["response"] = FakeResponse(status_code, body)
        state["error"] = error

    configure.calls = calls
    return configure
