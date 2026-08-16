import requests

from notifier_app.notifiers.pushover import PushoverNotifier


def make(conf=None):
    base = {"api_url": "http://gateway:8794", "app_token": "app", "user_key": "user"}
    base.update(conf or {})
    return PushoverNotifier(base)


def test_test_connection_validates_credentials(fake_requests):
    fake_requests(200, {"status": 1})
    outcome = make().test_connection()
    assert outcome["ok"] is True
    call = fake_requests.calls[0]
    assert call["url"] == "http://gateway:8794/1/users/validate.json"
    assert call["data"] == {"token": "app", "user": "user"}


def test_test_connection_requires_credentials(fake_requests):
    outcome = make({"app_token": ""}).test_connection()
    assert outcome["ok"] is False
    assert fake_requests.calls == []


def test_test_connection_reports_invalid_credentials(fake_requests):
    fake_requests(400, {"status": 0, "errors": ["user key is invalid"]})
    outcome = make().test_connection()
    assert outcome["ok"] is False
    assert "user key is invalid" in outcome["detail"]


def test_test_connection_reports_unreachable(fake_requests):
    fake_requests(error=requests.ConnectTimeout("timed out"))
    outcome = make().test_connection()
    assert outcome["ok"] is False
    assert "cannot reach http://gateway:8794" in outcome["detail"]


def test_send_posts_message_form(fake_requests):
    fake_requests(200, {"status": 1})
    outcome = make().send("hello", title="Hi", priority="low", options={"sound": "magic"})
    assert outcome["ok"] is True
    call = fake_requests.calls[0]
    assert call["url"] == "http://gateway:8794/1/messages.json"
    assert call["data"]["message"] == "hello"
    assert call["data"]["title"] == "Hi"
    assert call["data"]["priority"] == "-1"
    assert call["data"]["sound"] == "magic"


def test_send_emergency_priority_adds_retry_expire(fake_requests):
    fake_requests(200, {"status": 1})
    make().send("hello", priority="urgent")
    data = fake_requests.calls[0]["data"]
    assert data["priority"] == "2"
    assert data["retry"] == "60"
    assert data["expire"] == "3600"


def test_send_reports_api_errors(fake_requests):
    fake_requests(400, {"status": 0, "errors": ["application token is invalid"]})
    outcome = make().send("hello")
    assert outcome["ok"] is False
    assert "application token is invalid" in outcome["detail"]
