import logging
import threading
from dash.exceptions import PreventUpdate

logger = logging.getLogger(__name__)

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


def get(key):
    # Fast path: already cached
    with _lock:
        value = _store.get(key)
    if value is not None:
        return value

    factory = _factories.get(key)
    if not factory:
        raise PreventUpdate

    # Determine if we should load, or wait for another thread's load
    with _lock:
        # Re-check under lock (may have been populated while we waited)
        value = _store.get(key)
        if value is not None:
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
            if value is not None:
                set(key, value)
        except PreventUpdate:
            raise
        except Exception:
            logger.exception("server_cache: factory for '%s' failed", key)
            value = None
        finally:
            with _lock:
                _loading.pop(key, None)
            event.set()
    else:
        # Wait for the loading thread to finish (up to 30s)
        event.wait(timeout=30)
        with _lock:
            value = _store.get(key)

    if value is None:
        raise PreventUpdate
    return value


def has(key):
    with _lock:
        return key in _store
