import hmac
import os
import time

from flask import Flask, jsonify, request
from flask_login import LoginManager

from auth import User

server = Flask(__name__)
server.secret_key = os.getenv("SECRET_KEY")

login_manager = LoginManager()
login_manager.login_view = "/login"
login_manager.init_app(server)


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


# Cache clear endpoint: the data pipeline calls this after a load to drop
# stale parquet + server_store entries. Gated on CACHE_REFRESH_TOKEN shared
# secret; 503 when unset so we never expose an open cache-bust button.

def _check_refresh_token():
    expected = os.getenv("CACHE_REFRESH_TOKEN")
    if not expected:
        return jsonify({"error": "refresh endpoint disabled"}), 503
    provided = request.headers.get("X-Refresh-Token", "")
    if not hmac.compare_digest(provided, expected):
        return jsonify({"error": "unauthorized"}), 401
    return None


@server.route("/api/cache/clear", methods=["GET", "POST"])
def clear_cache_endpoint():
    err = _check_refresh_token()
    if err is not None:
        return err

    # Lazy imports: avoids circular import with queries/server_store at load.
    from queries import QueryService
    import server_store

    server_store.clear()
    QueryService.get_instance().clear_cache()
    return jsonify({"status": "ok", "cleared_at": time.time()})
