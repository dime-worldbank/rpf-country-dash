import logging
import threading
from dash.exceptions import PreventUpdate

logger = logging.getLogger(__name__)

_MISSING = object()  # sentinel to distinguish "not cached" from cached None

_store = {}
_factories = {}
_lock = threading.Lock()
_loading = {}  # key -> threading.Event


def register(key, factory):
    """Register a loader function that auto-populates the key on cache miss."""
    _factories[key] = factory


def set(key, value):
    with _lock:
        _store[key] = value


def lookup(key):
    """Return the cached value or raise KeyError. Dash-agnostic."""
    # Fast path: already cached
    with _lock:
        value = _store.get(key, _MISSING)
    if value is not _MISSING:
        return value

    factory = _factories.get(key)
    if not factory:
        raise KeyError(key)

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
        except KeyError:
            raise
        except Exception:
            logger.exception("server_cache: factory for '%s' failed", key)
            raise KeyError(key)
        finally:
            with _lock:
                _loading.pop(key, None)
            event.set()
    else:
        event.wait(timeout=30)
        with _lock:
            value = _store.get(key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)

    return value


def get(key):
    """Return the cached value, or raise PreventUpdate on miss.

    Convenience wrapper for Dash callbacks. For non-Dash code, use lookup().
    """
    try:
        return lookup(key)
    except KeyError:
        raise PreventUpdate


def has(key):
    with _lock:
        return key in _store
