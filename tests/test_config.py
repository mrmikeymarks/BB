import pytest

from notifier_app.config import ConfigStore


def make_store(tmp_path, environ=None):
    return ConfigStore(str(tmp_path / "config.json"), environ=environ or {})


def test_defaults(tmp_path):
    config = make_store(tmp_path).get()
    assert config["ntfy"]["server_url"] == "https://ntfy.sh"
    assert config["pushover"]["api_url"] == "https://api.pushover.net"
    assert config["ntfy"]["topic"] == ""


def test_environment_overrides_defaults(tmp_path):
    environ = {"NTFY_SERVER_URL": "http://nas.local:8093", "NTFY_TOPIC": "alerts"}
    config = make_store(tmp_path, environ).get()
    assert config["ntfy"]["server_url"] == "http://nas.local:8093"
    assert config["ntfy"]["topic"] == "alerts"


def test_saved_overrides_beat_environment(tmp_path):
    store = make_store(tmp_path, {"NTFY_SERVER_URL": "http://from-env"})
    store.update({"ntfy": {"server_url": "http://from-ui"}})
    assert store.get()["ntfy"]["server_url"] == "http://from-ui"


def test_update_persists_across_instances(tmp_path):
    make_store(tmp_path).update({"pushover": {"app_token": "abc123"}})
    fresh = make_store(tmp_path)
    assert fresh.get()["pushover"]["app_token"] == "abc123"


def test_null_clears_saved_override(tmp_path):
    environ = {"NTFY_TOPIC": "env-topic"}
    store = make_store(tmp_path, environ)
    store.update({"ntfy": {"topic": "ui-topic"}})
    assert store.get()["ntfy"]["topic"] == "ui-topic"
    store.update({"ntfy": {"topic": None}})
    assert store.get()["ntfy"]["topic"] == "env-topic"


def test_update_rejects_unknown_keys(tmp_path):
    store = make_store(tmp_path)
    with pytest.raises(ValueError):
        store.update({"telegram": {"token": "x"}})
    with pytest.raises(ValueError):
        store.update({"ntfy": {"bogus": "x"}})
    with pytest.raises(ValueError):
        store.update({"ntfy": {"topic": 5}})


def test_masked_hides_secrets(tmp_path):
    store = make_store(tmp_path)
    store.update({
        "ntfy": {"token": "tk_secret"},
        "pushover": {"app_token": "app", "user_key": ""},
    })
    masked = store.masked()
    assert masked["ntfy"]["token_configured"] is True
    assert "token" not in masked["ntfy"]
    assert masked["pushover"]["app_token_configured"] is True
    assert masked["pushover"]["user_key_configured"] is False
    assert "tk_secret" not in repr(masked)
