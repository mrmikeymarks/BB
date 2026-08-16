"""Web UI and JSON API."""

from flask import Blueprint, current_app, jsonify, render_template, request

from .config import SECRET_FIELDS
from .notifiers import PROVIDERS, build_notifiers

bp = Blueprint("main", __name__)
api = Blueprint("api", __name__, url_prefix="/api")


def _store():
    return current_app.extensions["config_store"]


@bp.get("/")
def index():
    return render_template("index.html", providers=sorted(PROVIDERS))


@bp.get("/privacy")
def privacy():
    return render_template("privacy.html")


@api.get("/health")
def health():
    return jsonify({"status": "ok", "providers": sorted(PROVIDERS)})


@api.get("/config")
def get_config():
    return jsonify(_store().masked())


@api.post("/config")
def update_config():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400
    # A blank secret submitted from the form means "keep the stored value".
    cleaned = {}
    for provider, fields in payload.items():
        if not isinstance(fields, dict):
            cleaned[provider] = fields
            continue
        secrets = SECRET_FIELDS.get(provider, set())
        cleaned[provider] = {
            field: value
            for field, value in fields.items()
            if not (field in secrets and value == "")
        }
    try:
        _store().update(cleaned)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_store().masked())


@api.post("/test/<provider>")
def test_provider(provider):
    notifiers = build_notifiers(_store().get())
    if provider not in notifiers:
        return jsonify({"error": "unknown provider: %s" % provider}), 404
    outcome = notifiers[provider].test_connection()
    return jsonify(outcome), 200 if outcome["ok"] else 502


@api.post("/notify")
def notify():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    providers = payload.get("providers")
    if not isinstance(providers, list) or not providers:
        return jsonify({"error": "providers must be a non-empty list"}), 400
    unknown = [p for p in providers if p not in PROVIDERS]
    if unknown:
        return jsonify({"error": "unknown providers: %s" % ", ".join(unknown)}), 400

    title = (payload.get("title") or "").strip() or None
    priority = payload.get("priority")
    options = payload.get("options") or {}

    notifiers = build_notifiers(_store().get())
    results = {}
    for name in providers:
        provider_options = options.get(name) if isinstance(options, dict) else None
        if not isinstance(provider_options, dict):
            provider_options = {}
        results[name] = notifiers[name].send(
            message, title=title, priority=priority, options=provider_options
        )

    succeeded = [n for n, r in results.items() if r["ok"]]
    if len(succeeded) == len(results):
        status = 200
    elif succeeded:
        status = 207
    else:
        status = 502
    return jsonify({"ok": len(succeeded) == len(results), "results": results}), status
