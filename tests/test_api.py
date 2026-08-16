import json

import requests


def configure_providers(client):
    payload = {
        "ntfy": {"server_url": "http://ntfy-box:8093", "topic": "alerts"},
        "pushover": {"api_url": "http://gateway:8794", "app_token": "app", "user_key": "user"},
    }
    resp = client.post("/api/config", json=payload)
    assert resp.status_code == 200


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
    assert set(resp.get_json()["providers"]) == {"ntfy", "pushover"}


def test_index_serves_ui(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"BB Notifier" in resp.data
    assert b'href="/privacy"' in resp.data


def test_privacy_page_has_carrier_required_statements(client):
    resp = client.get("/privacy")
    assert resp.status_code == 200
    text = b" ".join(resp.data.split())
    assert b"never shared with third parties or affiliates for marketing" in text
    assert b"excludes mobile opt-in" in text
    assert b"opt-in information is never shared" in text
    assert b"replying STOP, UNSUBSCRIBE, or QUIT" in text


def test_get_config_masks_secrets(client):
    client.post("/api/config", json={"ntfy": {"token": "tk_secret"}})
    resp = client.get("/api/config")
    body = resp.get_json()
    assert body["ntfy"]["token_configured"] is True
    assert "tk_secret" not in json.dumps(body)


def test_update_config_rejects_unknown_field(client):
    resp = client.post("/api/config", json={"ntfy": {"bogus": "x"}})
    assert resp.status_code == 400
    assert "bogus" in resp.get_json()["error"]


def test_blank_secret_keeps_stored_value(client, app):
    client.post("/api/config", json={"pushover": {"app_token": "keep-me"}})
    client.post("/api/config", json={"pushover": {"app_token": "", "api_url": "http://new"}})
    config = app.extensions["config_store"].get()
    assert config["pushover"]["app_token"] == "keep-me"
    assert config["pushover"]["api_url"] == "http://new"


def test_test_endpoint_unknown_provider(client):
    resp = client.post("/api/test/telegram")
    assert resp.status_code == 404


def test_test_endpoint_success(client, fake_requests):
    configure_providers(client)
    fake_requests(200, {"healthy": True})
    resp = client.post("/api/test/ntfy")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert fake_requests.calls[0]["url"] == "http://ntfy-box:8093/v1/health"


def test_test_endpoint_failure_returns_502(client, fake_requests):
    configure_providers(client)
    fake_requests(error=requests.ConnectionError("refused"))
    resp = client.post("/api/test/pushover")
    assert resp.status_code == 502
    assert resp.get_json()["ok"] is False


def test_notify_requires_message_and_providers(client):
    assert client.post("/api/notify", json={"providers": ["ntfy"]}).status_code == 400
    assert client.post("/api/notify", json={"message": "hi"}).status_code == 400
    resp = client.post("/api/notify", json={"message": "hi", "providers": ["nope"]})
    assert resp.status_code == 400


def test_notify_sends_to_both_providers(client, fake_requests):
    configure_providers(client)
    fake_requests(200, {"status": 1, "healthy": True})
    resp = client.post("/api/notify", json={
        "providers": ["ntfy", "pushover"],
        "title": "Hi",
        "message": "hello world",
        "priority": "high",
        "options": {"ntfy": {"tags": "bell"}},
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["results"]["ntfy"]["ok"] is True
    assert body["results"]["pushover"]["ok"] is True
    urls = [c["url"] for c in fake_requests.calls]
    assert "http://ntfy-box:8093/alerts" in urls
    assert "http://gateway:8794/1/messages.json" in urls


def test_notify_unconfigured_provider_fails_cleanly(client, fake_requests):
    resp = client.post("/api/notify", json={"providers": ["ntfy"], "message": "hi"})
    assert resp.status_code == 502
    body = resp.get_json()
    assert body["ok"] is False
    assert "topic" in body["results"]["ntfy"]["detail"]
    assert fake_requests.calls == []
