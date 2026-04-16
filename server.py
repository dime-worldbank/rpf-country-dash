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


# ---- External cache refresh endpoints ---------------------------------------
# The upstream data pipeline hits POST /api/cache/refresh after loading new
# data. The endpoint clears the persistent query cache, pre-warms every
# parameterless query, and clears the in-memory server_store so the dashboard
# picks up fresh data on the next request without waiting for a worker restart.
#
# Auth is a shared secret in CACHE_REFRESH_TOKEN. If unset, both endpoints
# return 503 so the app never exposes an open cache-bust button.

def _check_refresh_token():
    expected = os.getenv("CACHE_REFRESH_TOKEN")
    if not expected:
        return jsonify({"error": "refresh endpoint disabled"}), 503
    provided = request.headers.get("X-Refresh-Token", "")
    if not hmac.compare_digest(provided, expected):
        return jsonify({"error": "unauthorized"}), 401
    return None


@server.route("/api/cache/refresh", methods=["GET", "POST"])
def refresh_cache_endpoint():
    err = _check_refresh_token()
    if err is not None:
        return err

    # Local imports avoid a circular dependency at module load time.
    from queries import QueryService
    import server_store

    start = time.time()
    results = QueryService.get_instance().refresh_cache()
    server_store.clear()
    total_s = round(time.time() - start, 3)

    failed = [r for r in results if r.get("status") != "ok"]
    status_code = 200 if not failed else 207  # 207 = partial failure
    return (
        jsonify(
            {
                "refreshed_at": time.time(),
                "duration_s": total_s,
                "queries": results,
                "failed_count": len(failed),
            }
        ),
        status_code,
    )


@server.route("/api/cache/status", methods=["GET"])
def cache_status_endpoint():
    err = _check_refresh_token()
    if err is not None:
        return err

    from queries import QueryService

    return jsonify({"entries": QueryService.get_instance().cache_status()})
