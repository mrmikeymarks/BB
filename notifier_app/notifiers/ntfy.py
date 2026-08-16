"""Client for ntfy (https://ntfy.sh or any self-hosted ntfy server)."""

import base64

from .base import ConnectionFailure, Notifier, result


def header_value(value):
    """ntfy accepts RFC 2047 encoded words for non-Latin-1 header values."""
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return "=?UTF-8?B?%s?=" % encoded


class NtfyNotifier(Notifier):
    name = "ntfy"
    priority_map = {"min": 1, "low": 2, "normal": 3, "high": 4, "urgent": 5}

    @property
    def server_url(self):
        return (self.conf.get("server_url") or "").strip().rstrip("/")

    def _auth_headers(self):
        token = (self.conf.get("token") or "").strip()
        if token:
            return {"Authorization": "Bearer %s" % token}
        return {}

    def test_connection(self):
        if not self.server_url:
            return result(False, "ntfy server URL is not configured")
        url = "%s/v1/health" % self.server_url
        try:
            resp = self.request("GET", url)
        except ConnectionFailure as exc:
            return result(False, "cannot reach %s (%s)" % (self.server_url, exc))
        if resp.status_code != 200:
            return result(False, "%s answered HTTP %d" % (url, resp.status_code), resp.status_code)
        try:
            healthy = bool(resp.json().get("healthy"))
        except ValueError:
            healthy = True
        if not healthy:
            return result(False, "%s reports unhealthy" % self.server_url, resp.status_code)
        return result(True, "connected to ntfy server at %s" % self.server_url, resp.status_code)

    def _message_headers(self, title, priority, options):
        headers = self._auth_headers()
        if title:
            headers["X-Title"] = header_value(title)
        resolved = self.resolve_priority(priority)
        if resolved is not None:
            headers["X-Priority"] = str(resolved)
        tags = (options.get("tags") or "").strip()
        if tags:
            headers["X-Tags"] = header_value(tags)
        click = (options.get("click") or "").strip()
        if click:
            headers["X-Click"] = click
        return headers

    @staticmethod
    def _error_from(resp):
        try:
            return resp.json().get("error") or "HTTP %d" % resp.status_code
        except ValueError:
            return "HTTP %d" % resp.status_code

    def send(self, message, title=None, priority=None, options=None):
        if not self.server_url:
            return result(False, "ntfy server URL is not configured")
        topic = (self.conf.get("topic") or "").strip()
        if not topic:
            return result(False, "ntfy topic is not configured")
        if "/" in topic:
            return result(False, "ntfy topic must not contain '/'")

        headers = self._message_headers(title, priority, options or {})
        url = "%s/%s" % (self.server_url, topic)
        try:
            resp = self.request("POST", url, data=message.encode("utf-8"), headers=headers)
        except ConnectionFailure as exc:
            return result(False, "cannot reach %s (%s)" % (self.server_url, exc))
        if resp.status_code == 200:
            return result(True, "delivered to topic '%s' on %s" % (topic, self.server_url), 200)
        return result(False, "ntfy rejected the message: %s" % self._error_from(resp), resp.status_code)
