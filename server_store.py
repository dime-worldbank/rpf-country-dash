import copy
import logging
import threading
import pandas as pd
from dash.exceptions import PreventUpdate

logger = logging.getLogger(__name__)

_MISSING = object()  # sentinel to distinguish "not cached" from cached None

_store = {}
_lock = threading.Lock()


def _safe_copy(value):
    """Return a defensive copy for mutable types, passthrough for immutables."""
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return value


def set(key, value):
    with _lock:
        _store[key] = value


def _lookup_raw(key):
    """Return the raw cached value (no copy), or _MISSING if not found.

    On miss, auto-populates via data_mapping.function_data_mapping.
    """
    with _lock:
        value = _store.get(key, _MISSING)
    if value is not _MISSING:
        return value

    # Lazy import to avoid circular dependency (data_mapping imports server_store).
    from data_mapping import function_data_mapping
    loader = function_data_mapping.get(key)
    if not loader:
        return _MISSING

    try:
        logger.info("server_store: auto-populating '%s'", key)
        value = loader()
    except Exception:
        logger.exception("server_store: loader for '%s' failed", key)
        return _MISSING

    with _lock:
        # Another thread may have beaten us — use theirs
        existing = _store.get(key, _MISSING)
        if existing is not _MISSING:
            return existing
        _store[key] = value
    return value


def lookup(key, default=None):
    """Return a defensive copy of the cached value, or default if missing.

    Works like dict.get(key, default). For Dash callbacks, use get() instead.
    """
    value = _lookup_raw(key)
    if value is _MISSING:
        return default
    return _safe_copy(value)


def get(key):
    """Return a defensive copy of the cached value, or raise PreventUpdate.

    Convenience wrapper for Dash callbacks. For non-Dash code, use lookup().
    """
    value = _lookup_raw(key)
    if value is _MISSING:
        raise PreventUpdate
    return _safe_copy(value)


def has(key):
    with _lock:
        return key in _store


def clear():
    """Drop all cached values; factories stay registered and repopulate lazily."""
    with _lock:
        _store.clear()
    logger.info("server_store cleared")
