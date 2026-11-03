"""Parquet-backed query cache with an in-memory fast path.

Lookup order: memory → disk → miss. The parquet files on disk are the
source of truth; entries live until the /api/cache/clear endpoint in
server.py clears the whole cache.
"""

import glob
import hashlib
import logging
import os
import threading
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _hash_query(query_text: str) -> str:
    return hashlib.sha256(query_text.encode("utf-8")).hexdigest()


class PersistentQueryCache:
    """`namespace` separates entries of different data sources sharing one cache_dir;
    the empty namespace keys entries by the query text alone."""

    def __init__(self, cache_dir: str, namespace: str = ""):
        self._cache_dir = cache_dir
        self._namespace = namespace
        self._mem: dict[str, pd.DataFrame] = {}
        self._lock = threading.Lock()
        os.makedirs(self._cache_dir, exist_ok=True)

    def _key(self, query_text: str) -> str:
        if not self._namespace:
            return _hash_query(query_text)
        return _hash_query(f"{self._namespace}\n{query_text}")

    def _parquet_path(self, key_hash: str) -> str:
        return os.path.join(self._cache_dir, f"{key_hash}.parquet")

    def get(self, query_text: str) -> Optional[pd.DataFrame]:
        key_hash = self._key(query_text)
        path = self._parquet_path(key_hash)

        with self._lock:
            df = self._mem.get(key_hash)
            if df is not None:
                logger.info("CACHE HIT (mem) %s", query_text)
                return df.copy(deep=True)
            if not os.path.exists(path):
                return None

        try:
            df = pd.read_parquet(path)
        except Exception as e:
            logger.warning("Failed to read parquet cache for %s: %s", query_text, e)
            return None

        with self._lock:
            self._mem[key_hash] = df
        logger.info("CACHE HIT (disk) %s", query_text)
        return df.copy(deep=True)

    def set(self, query_text: str, df: pd.DataFrame) -> None:
        key_hash = self._key(query_text)
        path = self._parquet_path(key_hash)

        try:
            df.to_parquet(path, index=False)
        except Exception as e:
            logger.warning("Failed to write parquet cache for %s: %s", query_text, e)
            with self._lock:
                self._mem[key_hash] = df
            return

        with self._lock:
            self._mem[key_hash] = df

    def clear(self) -> None:
        with self._lock:
            self._mem.clear()
            for path in glob.glob(os.path.join(self._cache_dir, "*.parquet")):
                try:
                    os.remove(path)
                except OSError as e:
                    logger.warning("Failed to remove %s: %s", path, e)
        logger.info("Persistent query cache cleared")
