"""
Persistent query cache backed by parquet files on local disk.

Lookup order in `get(query_text)`:
  1. In-memory dict (fast path for repeat hits in the same process)
  2. Parquet file on disk (survives worker/process restarts)
  3. None (caller should run the query and call `set` with the result)

The cache is invalidated primarily by the external refresh endpoint
(see `server.py`), not by TTL. The TTL acts only as a safety ceiling so
a broken pipeline can't serve stale data forever.
"""

import hashlib
import json
import logging
import os
import threading
import time
from typing import Optional

import pandas as pd


# Use the root logger (configured by queries.py via basicConfig) rather than
# a module logger, so INFO-level cache hit/miss lines surface on Posit Connect
# regardless of how gunicorn has configured handlers.
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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

    # ---- index (hash -> {query, written_at}) ---------------------------------
    def _load_index(self) -> dict:
        try:
            with open(self._index_path, "r") as f:
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

    # ---- public API ----------------------------------------------------------
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
                # expired in memory; drop and fall through to disk
                del self._mem[key_hash]

            entry = self._index.get(key_hash)
            if entry is None:
                return None
            written_at = entry.get("written_at", 0)
            if now - written_at >= self._ttl:
                return None
            path = self._parquet_path(key_hash)
            if not os.path.exists(path):
                # stale index entry; clean it up
                self._index.pop(key_hash, None)
                self._save_index_locked()
                return None

        # Read parquet outside the lock (I/O); then populate memory.
        try:
            df = pd.read_parquet(path)
        except Exception as e:
            logger.warning("Failed to read parquet cache for %s: %s", query_text, e)
            return None

        with self._lock:
            self._mem[key_hash] = (written_at, df)
        logger.info("CACHE HIT (disk) %s", query_text)
        return df.copy(deep=True)

    def set(self, query_text: str, df: pd.DataFrame) -> None:
        key_hash = _hash_query(query_text)
        path = self._parquet_path(key_hash)
        now = time.time()

        # Write parquet outside the lock (I/O).
        try:
            df.to_parquet(path, index=False)
        except Exception as e:
            logger.warning("Failed to write parquet cache for %s: %s", query_text, e)
            # Still cache in memory so the current process benefits.
            with self._lock:
                self._mem[key_hash] = (now, df)
            return

        with self._lock:
            if len(self._mem) >= self._max_entries:
                oldest = next(iter(self._mem))
                del self._mem[oldest]
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
            # Delete parquet files for entries we know about; leave unknown files alone.
            for key_hash in list(self._index.keys()):
                path = self._parquet_path(key_hash)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError as e:
                    logger.warning("Failed to remove %s: %s", path, e)
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
            path = self._parquet_path(key_hash)
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError as e:
                logger.warning("Failed to remove %s: %s", path, e)
        return removed_mem or removed_index

    def status(self) -> list[dict]:
        with self._lock:
            out = []
            for key_hash, entry in self._index.items():
                path = self._parquet_path(key_hash)
                try:
                    size = os.path.getsize(path) if os.path.exists(path) else None
                except OSError:
                    size = None
                out.append(
                    {
                        "hash": key_hash,
                        "query": entry.get("query"),
                        "written_at": entry.get("written_at"),
                        "rows": entry.get("rows"),
                        "size_bytes": size,
                    }
                )
            return out
