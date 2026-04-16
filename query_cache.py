"""Parquet-backed query cache with an in-memory fast path.

Lookup order: memory → disk → miss. TTL is a safety ceiling; primary
invalidation is the /api/cache/clear endpoint in server.py.
"""

import hashlib
import json
import logging
import os
import threading
import time
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _hash_query(query_text: str) -> str:
    return hashlib.sha256(query_text.encode("utf-8")).hexdigest()


class PersistentQueryCache:
    def __init__(self, cache_dir: str, ttl_seconds: int, max_entries: int):
        self._cache_dir = cache_dir
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._mem: dict[str, tuple[float, pd.DataFrame]] = {}
        self._lock = threading.Lock()
        os.makedirs(self._cache_dir, exist_ok=True)
        self._index_path = os.path.join(self._cache_dir, "index.json")
        self._index = self._load_index()

    # Index maps query hash -> {query, written_at, rows}.
    def _load_index(self) -> dict:
        try:
            with open(self._index_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_index_locked(self) -> None:
        tmp = self._index_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._index, f, indent=2)
        os.replace(tmp, self._index_path)

    def _parquet_path(self, key_hash: str) -> str:
        return os.path.join(self._cache_dir, f"{key_hash}.parquet")

    def get(self, query_text: str) -> Optional[pd.DataFrame]:
        key_hash = _hash_query(query_text)
        now = time.time()

        with self._lock:
            hit = self._mem.get(key_hash)
            if hit is not None:
                written_at, df = hit
                if now - written_at < self._ttl:
                    logger.info("CACHE HIT (mem) %s", query_text)
                    return df.copy(deep=True)
                del self._mem[key_hash]

            entry = self._index.get(key_hash)
            if entry is None or now - entry.get("written_at", 0) >= self._ttl:
                return None
            path = self._parquet_path(key_hash)
            if not os.path.exists(path):
                self._index.pop(key_hash, None)
                self._save_index_locked()
                return None
            written_at = entry["written_at"]

        try:
            df = pd.read_parquet(path)
        except Exception as e:
            logger.warning("Failed to read parquet cache for %s: %s", query_text, e)
            return None

        with self._lock:
            # Skip the mem populate if another thread invalidated or rewrote
            # this entry while we were reading — otherwise we'd orphan stale
            # data in _mem past any subsequent invalidation.
            current = self._index.get(key_hash)
            if current is not None and current.get("written_at") == written_at:
                self._mem[key_hash] = (written_at, df)
        logger.info("CACHE HIT (disk) %s", query_text)
        return df.copy(deep=True)

    def set(self, query_text: str, df: pd.DataFrame) -> None:
        key_hash = _hash_query(query_text)
        path = self._parquet_path(key_hash)
        now = time.time()

        try:
            df.to_parquet(path, index=False)
        except Exception as e:
            logger.warning("Failed to write parquet cache for %s: %s", query_text, e)
            with self._lock:
                self._mem[key_hash] = (now, df)
            return

        with self._lock:
            if len(self._mem) >= self._max_entries:
                del self._mem[next(iter(self._mem))]  # FIFO eviction
            self._mem[key_hash] = (now, df)
            self._index[key_hash] = {
                "query": query_text,
                "written_at": now,
                "rows": int(len(df)),
            }
            self._save_index_locked()

    def clear(self) -> None:
        with self._lock:
            self._mem.clear()
            for key_hash in list(self._index):
                self._remove_parquet(key_hash)
            self._index = {}
            self._save_index_locked()
        logger.info("Persistent query cache cleared")

    def invalidate(self, query_text: str) -> bool:
        key_hash = _hash_query(query_text)
        with self._lock:
            removed_mem = self._mem.pop(key_hash, None) is not None
            removed_index = self._index.pop(key_hash, None) is not None
            if removed_index:
                self._save_index_locked()
            self._remove_parquet(key_hash)
        return removed_mem or removed_index

    def _remove_parquet(self, key_hash: str) -> None:
        path = self._parquet_path(key_hash)
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            logger.warning("Failed to remove %s: %s", path, e)

    def status(self) -> list[dict]:
        with self._lock:
            out = []
            for key_hash, entry in self._index.items():
                path = self._parquet_path(key_hash)
                size = os.path.getsize(path) if os.path.exists(path) else None
                out.append({"hash": key_hash, **entry, "size_bytes": size})
            return out
