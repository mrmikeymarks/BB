# BB Notifier

A small Flask web app that sends push notifications through **Pushover** and **ntfy**.
Both providers have configurable server URLs, so the app can connect to services running
on another server — e.g. a self-hosted [ntfy](https://docs.ntfy.sh/install/) instance on a
NAS/home server, or a Pushover-compatible gateway — as well as the official hosted services.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8080 — the UI lets you set each provider's server/credentials,
run a **Test connection** against the remote server, and send notifications to either
or both providers.

To make the app reachable from other machines on your network:

```bash
HOST=0.0.0.0 PORT=8080 python app.py
```

## Configuring the providers

Settings come from three layers; later layers win:

1. Built-in defaults (`https://ntfy.sh`, `https://api.pushover.net`)
2. Environment variables
3. Values saved from the web UI / `POST /api/config` (persisted to `instance/config.json`,
   see [config.example.json](config.example.json) for the shape)

| Environment variable | Meaning |
| --- | --- |
| `NTFY_SERVER_URL` | Base URL of the ntfy server, e.g. `http://192.168.1.50:8093` |
| `NTFY_TOPIC` | Topic to publish to, e.g. `bb-alerts` |
| `NTFY_TOKEN` | Optional access token for protected ntfy servers |
| `PUSHOVER_API_URL` | Pushover API base URL (default `https://api.pushover.net`) |
| `PUSHOVER_APP_TOKEN` | Pushover application/API token |
| `PUSHOVER_USER_KEY` | Pushover user key |

Example — point the app at an ntfy server running on another machine:

```bash
NTFY_SERVER_URL=http://192.168.1.50:8093 NTFY_TOPIC=bb-alerts python app.py
```

- **ntfy:** connection tests use the server's `/v1/health` endpoint; messages are published
  as `POST {server}/{topic}` with title/priority/tags/click headers and optional
  `Authorization: Bearer` token.
- **Pushover:** connection tests call `POST {api}/1/users/validate.json` with your
  credentials; messages go to `POST {api}/1/messages.json`. Get a user key and app token
  at [pushover.net](https://pushover.net/) (Pushover itself is a hosted service; the base
  URL override exists for proxies/compatible gateways).

## HTTP API

| Endpoint | Description |
| --- | --- |
| `GET /api/health` | App health and available providers |
| `GET /api/config` | Effective config (secrets masked as `*_configured` flags) |
| `POST /api/config` | Partial update, e.g. `{"ntfy": {"server_url": "http://..."}}`; `null` clears a saved value |
| `POST /api/test/<provider>` | Test connectivity to the configured server (`ntfy` or `pushover`); 200 on success, 502 on failure |
| `POST /api/notify` | Send a notification |

Send to both providers:

```bash
curl -sS -X POST http://127.0.0.1:8080/api/notify \
  -H 'Content-Type: application/json' \
  -d '{
        "providers": ["ntfy", "pushover"],
        "title": "Backup finished",
        "message": "Everything went fine.",
        "priority": "high",
        "options": {
          "ntfy": {"tags": "white_check_mark", "click": "https://example.org/status"},
          "pushover": {"sound": "magic"}
        }
      }'
```

`priority` accepts `min`, `low`, `normal`, `high`, `urgent` (mapped to each provider's
native scale) or a provider-native integer. The response contains a per-provider result;
the status code is 200 if all deliveries succeeded, 207 if some did, 502 if none did.

## Tests

```bash
pip install pytest
pytest
```

The suite mocks all outgoing HTTP, so it runs offline. CI (`.github/workflows/python-app.yml`)
runs flake8 and pytest on every push/PR to `main`.
