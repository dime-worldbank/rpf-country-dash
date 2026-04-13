import threading

_store = {}
_lock = threading.Lock()


def set(key, value):
    with _lock:
        _store[key] = value


def get(key):
    with _lock:
        return _store.get(key)


def has(key):
    with _lock:
        return key in _store
