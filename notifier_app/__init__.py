"""BB Notifier — a small Flask web app that sends notifications through
Pushover and ntfy, each pointed at a configurable server URL so it can talk
to self-hosted or remote instances of those services."""

import os

from flask import Flask

from .config import ConfigStore

__version__ = "0.1.0"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    test_config = test_config or {}
    app.config.update(test_config)

    config_path = test_config.get("CONFIG_PATH")
    if config_path is None:
        os.makedirs(app.instance_path, exist_ok=True)
        config_path = os.path.join(app.instance_path, "config.json")

    environ = test_config.get("ENVIRON")
    if environ is None:
        environ = os.environ

    app.extensions["config_store"] = ConfigStore(config_path, environ=environ)

    from . import routes

    app.register_blueprint(routes.bp)
    app.register_blueprint(routes.api)

    return app
