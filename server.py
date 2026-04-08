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

# Posit Connect serves content under a prefix like "/content/<guid>/" and
# passes the full path to the app rather than stripping the prefix. Dash knows
# about this via DASH_URL_BASE_PATHNAME and registers its own routes at the
# prefixed paths, but plain @server.route() registrations don't — so we have
# to register each API route at BOTH the bare path (for local dev) and the
# prefixed path (for Connect). The helper below does that once per route.
URL_PREFIX = os.getenv("DASH_URL_BASE_PATHNAME", "").rstrip("/")


def _register_api_route(rule, **options):
    """Register a Flask view at both the bare rule and the Connect-prefixed
    rule. When URL_PREFIX is empty (local dev) only the bare rule registers."""
    def decorator(view_func):
        server.add_url_rule(
            rule,
            endpoint=view_func.__name__,
            view_func=view_func,
            **options,
        )
        if URL_PREFIX:
            server.add_url_rule(
                f"{URL_PREFIX}{rule}",
                endpoint=f"{view_func.__name__}__prefixed",
                view_func=view_func,
                **options,
            )
        return view_func
    return decorator


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


# ---- Deploy marker endpoint --------------------------------------------------
# Trivial unauthenticated endpoint used to verify whether a new rsconnect
# deploy has actually landed on Posit Connect. Hit /api/version in a browser;
# if you see the JSON below, the new code is running. If you see the dashboard
# HTML, the deploy didn't take effect.
@_register_api_route("/api/version", methods=["GET"])
def version_endpoint():
    return jsonify({
        "marker": "cache-refresh-deploy-check-2026-04-08",
        "status": "ok",
        "url_prefix": URL_PREFIX or "(none)",
        "request_path": request.path,
    })


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


@_register_api_route("/api/cache/refresh", methods=["GET", "POST"])
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


@_register_api_route("/api/cache/status", methods=["GET"])
def cache_status_endpoint():
    ok, err = _check_refresh_token()
    if not ok:
        return err

    from queries import QueryService

    db = QueryService.get_instance()
    return jsonify({"entries": db.cache_status()})
