"""Client for the Pushover message API (api.pushover.net or a compatible
gateway/proxy reachable at a custom base URL)."""

from .base import ConnectionFailure, Notifier, result


class PushoverNotifier(Notifier):
    name = "pushover"
    priority_map = {"min": -2, "low": -1, "normal": 0, "high": 1, "urgent": 2}

    @property
    def api_url(self):
        return (self.conf.get("api_url") or "").strip().rstrip("/")

    def _credentials(self):
        return (
            (self.conf.get("app_token") or "").strip(),
            (self.conf.get("user_key") or "").strip(),
        )

    @staticmethod
    def _errors_from(resp, fallback):
        try:
            body = resp.json()
        except ValueError:
            return fallback
        errors = body.get("errors")
        if isinstance(errors, list) and errors:
            return "; ".join(str(e) for e in errors)
        return fallback

    def test_connection(self):
        if not self.api_url:
            return result(False, "Pushover API URL is not configured")
        token, user = self._credentials()
        if not token or not user:
            return result(False, "Pushover app token and user key are not configured")
        url = "%s/1/users/validate.json" % self.api_url
        try:
            resp = self.request("POST", url, data={"token": token, "user": user})
        except ConnectionFailure as exc:
            return result(False, "cannot reach %s (%s)" % (self.api_url, exc))
        if resp.status_code == 200:
            return result(True, "connected to %s and credentials are valid" % self.api_url, 200)
        detail = self._errors_from(resp, "HTTP %d" % resp.status_code)
        return result(False, "server at %s rejected credentials: %s" % (self.api_url, detail), resp.status_code)

    def _message_payload(self, token, user, message, title, priority, options):
        payload = {"token": token, "user": user, "message": message}
        if title:
            payload["title"] = title
        resolved = self.resolve_priority(priority)
        if resolved is not None:
            payload["priority"] = str(resolved)
            if resolved == 2:
                # Pushover requires retry/expire for emergency priority.
                payload["retry"] = str(options.get("retry") or 60)
                payload["expire"] = str(options.get("expire") or 3600)
        for field in ("sound", "device", "url", "url_title"):
            value = str(options.get(field) or "").strip()
            if value:
                payload[field] = value
        return payload

    def send(self, message, title=None, priority=None, options=None):
        if not self.api_url:
            return result(False, "Pushover API URL is not configured")
        token, user = self._credentials()
        if not token or not user:
            return result(False, "Pushover app token and user key are not configured")

        payload = self._message_payload(token, user, message, title, priority, options or {})
        endpoint = "%s/1/messages.json" % self.api_url
        try:
            resp = self.request("POST", endpoint, data=payload)
        except ConnectionFailure as exc:
            return result(False, "cannot reach %s (%s)" % (self.api_url, exc))
        if resp.status_code == 200:
            return result(True, "delivered via Pushover server at %s" % self.api_url, 200)
        detail = self._errors_from(resp, "HTTP %d" % resp.status_code)
        return result(False, "Pushover rejected the message: %s" % detail, resp.status_code)
