"""Runtime configuration for the notification providers.

Precedence (highest wins): values saved from the UI/API (persisted to a JSON
file in the Flask instance folder) > environment variables > built-in defaults.
"""

import copy
import json
import os
import threading

DEFAULTS = {
    "ntfy": {
        "server_url": "https://ntfy.sh",
        "topic": "",
        "token": "",
    },
    "pushover": {
        "api_url": "https://api.pushover.net",
        "app_token": "",
        "user_key": "",
    },
}

ENV_MAP = {
    ("ntfy", "server_url"): "NTFY_SERVER_URL",
    ("ntfy", "topic"): "NTFY_TOPIC",
    ("ntfy", "token"): "NTFY_TOKEN",
    ("pushover", "api_url"): "PUSHOVER_API_URL",
    ("pushover", "app_token"): "PUSHOVER_APP_TOKEN",
    ("pushover", "user_key"): "PUSHOVER_USER_KEY",
}

SECRET_FIELDS = {
    "ntfy": {"token"},
    "pushover": {"app_token", "user_key"},
}


class ConfigStore:
    """Thread-safe provider config backed by a sparse JSON overrides file."""

    def __init__(self, path, environ=None):
        self.path = path
        self.environ = environ if environ is not None else os.environ
        self._lock = threading.Lock()

    def _load_overrides(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_overrides(self, overrides):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(overrides, fh, indent=2)

    def get(self):
        """Return the effective config: defaults <- env <- saved overrides."""
        with self._lock:
            overrides = self._load_overrides()
        merged = copy.deepcopy(DEFAULTS)
        for (provider, field), env_name in ENV_MAP.items():
            value = self.environ.get(env_name)
            if value is not None:
                merged[provider][field] = value
        for provider, fields in overrides.items():
            if provider not in merged or not isinstance(fields, dict):
                continue
            for field, value in fields.items():
                if field in merged[provider] and isinstance(value, str):
                    merged[provider][field] = value
        return merged

    @staticmethod
    def _validate(changes):
        if not isinstance(changes, dict):
            raise ValueError("config payload must be an object")
        for provider, fields in changes.items():
            if provider not in DEFAULTS:
                raise ValueError("unknown provider: %s" % provider)
            if not isinstance(fields, dict):
                raise ValueError("config for %s must be an object" % provider)
            for field, value in fields.items():
                if field not in DEFAULTS[provider]:
                    raise ValueError("unknown field: %s.%s" % (provider, field))
                if value is not None and not isinstance(value, str):
                    raise ValueError("%s.%s must be a string or null" % (provider, field))

    def update(self, changes):
        """Apply partial changes and persist them.

        A value of None removes the saved override (falling back to the
        environment variable or default); a string sets it. Unknown providers
        or fields raise ValueError.
        """
        self._validate(changes)
        with self._lock:
            overrides = self._load_overrides()
            for provider, fields in changes.items():
                section = overrides.setdefault(provider, {})
                for field, value in fields.items():
                    if value is None:
                        section.pop(field, None)
                    else:
                        section[field] = value
                if not section:
                    overrides.pop(provider, None)
            self._save_overrides(overrides)
        return self.get()

    def masked(self):
        """Effective config with secret values replaced by *_configured flags."""
        merged = self.get()
        out = {}
        for provider, fields in merged.items():
            out[provider] = {}
            for field, value in fields.items():
                if field in SECRET_FIELDS.get(provider, set()):
                    out[provider][field + "_configured"] = bool(value)
                else:
                    out[provider][field] = value
        return out
