import hmac
import logging
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

logger = logging.getLogger(__name__)


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


# ---- External cache refresh endpoints ----------------------------------------
# The upstream data pipeline hits POST /api/cache/refresh after loading new
# data. The endpoint clears the persistent query cache and pre-warms every
# parameterless query so the first dashboard visitor gets instant loads.
# Auth is a shared secret in the CACHE_REFRESH_TOKEN env var. If that env var
# is unset both endpoints return 503 so the app never exposes an open
# cache-bust button.

def _check_refresh_token() -> tuple[bool, tuple]:
    expected = os.getenv("CACHE_REFRESH_TOKEN")
    if not expected:
        return False, (jsonify({"error": "refresh endpoint disabled"}), 503)
    provided = request.headers.get("X-Refresh-Token", "")
    if not hmac.compare_digest(provided, expected):
        return False, (jsonify({"error": "unauthorized"}), 401)
    return True, (None, None)


@server.route("/api/cache/refresh", methods=["POST"])
def refresh_cache_endpoint():
    ok, err = _check_refresh_token()
    if not ok:
        return err

    # Local import to avoid circular dependency at module load time.
    from queries import QueryService

    start = time.time()
    db = QueryService.get_instance()
    results = db.refresh_cache()
    total_s = round(time.time() - start, 3)

    failed = [r for r in results if r.get("status") != "ok"]
    status_code = 200 if not failed else 207  # 207 Multi-Status for partial failure
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
    ok, err = _check_refresh_token()
    if not ok:
        return err

    from queries import QueryService

    db = QueryService.get_instance()
    return jsonify({"entries": db.cache_status()})
