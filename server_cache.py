import logging
import threading

_store = {}
_lock = threading.Lock()
logger = logging.getLogger(__name__)


def set(key, value):
    with _lock:
        _store[key] = value


def get(key, default=None):
    with _lock:
        value = _store.get(key)
    if value is None:
        logger.warning("server_cache miss for key: %s", key)
        return default
    return value


def has(key):
    with _lock:
        return key in _store
