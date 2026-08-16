import requests

from notifier_app.notifiers.ntfy import NtfyNotifier, header_value


def make(conf=None):
    base = {"server_url": "http://ntfy-box:8093", "topic": "alerts", "token": ""}
    base.update(conf or {})
    return NtfyNotifier(base)


def test_test_connection_hits_health_endpoint(fake_requests):
    fake_requests(200, {"healthy": True})
    outcome = make().test_connection()
    assert outcome["ok"] is True
    call = fake_requests.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "http://ntfy-box:8093/v1/health"


def test_test_connection_reports_unreachable(fake_requests):
    fake_requests(error=requests.ConnectionError("refused"))
    outcome = make().test_connection()
    assert outcome["ok"] is False
    assert "cannot reach http://ntfy-box:8093" in outcome["detail"]


def test_test_connection_requires_server_url(fake_requests):
    outcome = make({"server_url": ""}).test_connection()
    assert outcome["ok"] is False
    assert fake_requests.calls == []


def test_send_posts_to_topic_with_headers(fake_requests):
    fake_requests(200, {"id": "m1"})
    outcome = make({"token": "tk_x"}).send(
        "hello", title="Title", priority="high", options={"tags": "warning", "click": "http://x"}
    )
    assert outcome["ok"] is True
    call = fake_requests.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "http://ntfy-box:8093/alerts"
    assert call["data"] == b"hello"
    headers = call["headers"]
    assert headers["X-Title"] == "Title"
    assert headers["X-Priority"] == "4"
    assert headers["X-Tags"] == "warning"
    assert headers["X-Click"] == "http://x"
    assert headers["Authorization"] == "Bearer tk_x"


def test_send_requires_topic(fake_requests):
    outcome = make({"topic": ""}).send("hello")
    assert outcome["ok"] is False
    assert "topic" in outcome["detail"]
    assert fake_requests.calls == []


def test_send_reports_server_error(fake_requests):
    fake_requests(403, {"error": "forbidden"})
    outcome = make().send("hello")
    assert outcome["ok"] is False
    assert "forbidden" in outcome["detail"]
    assert outcome["status"] == 403


def test_non_latin_title_is_rfc2047_encoded():
    encoded = header_value("Résumé ✓")
    assert encoded.startswith("=?UTF-8?B?")
    assert header_value("plain ascii") == "plain ascii"
