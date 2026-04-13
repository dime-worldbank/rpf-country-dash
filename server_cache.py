import threading
from dash.exceptions import PreventUpdate

_store = {}
_lock = threading.Lock()


def set(key, value):
    with _lock:
        _store[key] = value


def get(key):
    with _lock:
        value = _store.get(key)
    if value is None:
        raise PreventUpdate
    return value


def has(key):
    with _lock:
        return key in _store
