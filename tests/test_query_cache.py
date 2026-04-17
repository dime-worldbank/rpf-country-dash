import os
import tempfile
import threading
import unittest

import pandas as pd

from query_cache import PersistentQueryCache, _hash_query


class TestPersistentQueryCache(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache_dir = self._tmp.name
        self.df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

    def tearDown(self):
        self._tmp.cleanup()

    def _make(self, max_entries=256):
        return PersistentQueryCache(self.cache_dir, max_entries)

    def test_hash_is_stable(self):
        self.assertEqual(_hash_query("SELECT 1"), _hash_query("SELECT 1"))

    def test_hash_is_whitespace_sensitive(self):
        self.assertNotEqual(_hash_query("SELECT 1"), _hash_query("SELECT  1"))

    def test_miss_returns_none(self):
        self.assertIsNone(self._make().get("SELECT 1"))

    def test_set_then_get_hits_memory_tier(self):
        cache = self._make()
        cache.set("SELECT 1", self.df)
        pd.testing.assert_frame_equal(cache.get("SELECT 1"), self.df)

    def test_get_returns_defensive_copy(self):
        cache = self._make()
        cache.set("SELECT 1", self.df)
        retrieved = cache.get("SELECT 1")
        retrieved["a"] = [99, 99, 99]
        pd.testing.assert_frame_equal(cache.get("SELECT 1"), self.df)

    def test_disk_tier_survives_new_instance(self):
        """A fresh instance on the same cache_dir sees previously-written parquet."""
        self._make().set("SELECT 1", self.df)
        pd.testing.assert_frame_equal(self._make().get("SELECT 1"), self.df)

    def test_disk_tier_miss_after_parquet_removed(self):
        """If the parquet was deleted externally, get() returns None."""
        cache = self._make()
        cache.set("SELECT 1", self.df)
        os.remove(os.path.join(self.cache_dir, f"{_hash_query('SELECT 1')}.parquet"))
        self.assertIsNone(self._make().get("SELECT 1"))

    def test_clear_empties_memory_and_disk(self):
        cache = self._make()
        cache.set("SELECT 1", self.df)
        cache.set("SELECT 2", self.df)
        cache.clear()

        self.assertIsNone(cache.get("SELECT 1"))
        self.assertEqual({}, cache._mem)
        leftover = [f for f in os.listdir(self.cache_dir) if f.endswith(".parquet")]
        self.assertEqual([], leftover)

    def test_memory_eviction_respects_max_entries(self):
        cache = self._make(max_entries=2)
        cache.set("a", self.df)
        cache.set("b", self.df)
        cache.set("c", self.df)  # evicts oldest
        self.assertLessEqual(len(cache._mem), 2)

    def test_concurrent_set_is_safe(self):
        cache = self._make()
        errors = []

        def writer(i):
            try:
                cache.set(f"SELECT {i}", self.df)
            except Exception as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        self.assertEqual([], errors)
        parquets = [f for f in os.listdir(self.cache_dir) if f.endswith(".parquet")]
        self.assertEqual(20, len(parquets))


if __name__ == "__main__":
    unittest.main()
