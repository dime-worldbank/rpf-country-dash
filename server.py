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




def _check_refresh_token():
    expected = os.getenv("CACHE_REFRESH_TOKEN")
    if not expected:
        return jsonify({"error": "refresh endpoint disabled"}), 503
    provided = request.headers.get("X-Refresh-Token", "")
    if not hmac.compare_digest(provided, expected):
        return jsonify({"error": "unauthorized"}), 401
    return None


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


# Registered at both the unprefixed path (local/dev) and under DEFAULT_ROOT_PATH
# (deployed behind the rsconnect content prefix).
URL_PREFIX = os.getenv("DEFAULT_ROOT_PATH", "/").strip("/")

_routes = [("/api/cache/clear", "")]
if URL_PREFIX:
    _routes.append((f"/{URL_PREFIX}/api/cache/clear", "__prefixed"))

for path, suffix in _routes:
    server.add_url_rule(
        path,
        endpoint=f"{clear_cache_endpoint.__name__}{suffix}",
        view_func=clear_cache_endpoint,
        methods=["GET", "POST"],
    )