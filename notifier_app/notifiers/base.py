"""Shared plumbing for notification providers."""

import requests

DEFAULT_TIMEOUT = 10


def result(ok, detail, status=None, extra=None):
    payload = {"ok": bool(ok), "detail": detail, "status": status}
    if extra:
        payload.update(extra)
    return payload


class Notifier:
    """A provider client. Methods never raise; they return result() dicts so
    the API layer can report per-provider outcomes uniformly."""

    name = ""
    # Generic priority names accepted by the API, mapped per provider.
    priority_map = {}

    def __init__(self, conf, timeout=DEFAULT_TIMEOUT):
        self.conf = conf
        self.timeout = timeout

    def resolve_priority(self, priority):
        """Accept a generic name ("min"/"low"/"normal"/"high"/"urgent") or a
        provider-native integer; return the provider value or None."""
        if priority is None or priority == "":
            return None
        if isinstance(priority, int):
            return priority
        key = str(priority).strip().lower()
        if key in self.priority_map:
            return self.priority_map[key]
        try:
            return int(key)
        except ValueError:
            return None

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        try:
            return requests.request(method, url, **kwargs)
        except requests.RequestException as exc:
            raise ConnectionFailure("%s: %s" % (type(exc).__name__, exc))

    def test_connection(self):
        raise NotImplementedError

    def send(self, message, title=None, priority=None, options=None):
        raise NotImplementedError


class ConnectionFailure(Exception):
    """Raised by Notifier.request when the remote server cannot be reached."""
