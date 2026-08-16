"""Entry point: `python app.py` (or point a WSGI server at app:app)."""

import os

from notifier_app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    debug = os.environ.get("FLASK_DEBUG", "") == "1"
    app.run(host=host, port=port, debug=debug)
