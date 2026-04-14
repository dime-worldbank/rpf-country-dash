import copy
import logging
import threading
import pandas as pd
from dash.exceptions import PreventUpdate

logger = logging.getLogger(__name__)

_MISSING = object()  # sentinel to distinguish "not cached" from cached None

_store = {}
_factories = {}
_lock = threading.Lock()
_loading = {}  # key -> threading.Event


def _safe_copy(value):
    """Return a defensive copy for mutable types, passthrough for immutables."""
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, dict):
        return copy.deepcopy(value)
    return value


def register(key, factory):
    """Register a loader function that auto-populates the key on cache miss."""
    _factories[key] = factory


def set(key, value):
    with _lock:
        _store[key] = value


def _lookup_raw(key):
    """Return the raw cached value (no copy), or _MISSING if not found.

    If a factory is registered, auto-populates on miss.
    """
    # Fast path: already cached
    with _lock:
        value = _store.get(key, _MISSING)
    if value is not _MISSING:
        return value

    factory = _factories.get(key)
    if not factory:
        return _MISSING

    # Determine if we should load, or wait for another thread's load
    with _lock:
        value = _store.get(key, _MISSING)
        if value is not _MISSING:
            return value

        event = _loading.get(key)
        if event is not None:
            is_loader = False
        else:
            is_loader = True
            event = threading.Event()
            _loading[key] = event

    if is_loader:
        try:
            logger.info("server_cache: auto-populating '%s' via factory", key)
            value = factory()
            set(key, value)
            return value
        except Exception:
            logger.exception("server_cache: factory for '%s' failed", key)
            return _MISSING
        finally:
            with _lock:
                _loading.pop(key, None)
            event.set()
    else:
        event.wait(timeout=30)
        with _lock:
            return _store.get(key, _MISSING)


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
