import unittest
import threading
import time
from dash.exceptions import PreventUpdate
import server_cache


class TestServerCache(unittest.TestCase):
    """Tests for server_cache module."""

    def setUp(self):
        """Reset cache state between tests."""
        server_cache._store.clear()
        server_cache._factories.clear()
        server_cache._loading.clear()

    # ------------------------------------------------------------------
    # Basic get/set/has
    # ------------------------------------------------------------------

    def test_set_and_get(self):
        server_cache.set("k", "v")
        self.assertEqual(server_cache.get("k"), "v")

    def test_has_returns_true_for_existing_key(self):
        server_cache.set("k", 42)
        self.assertTrue(server_cache.has("k"))

    def test_has_returns_false_for_missing_key(self):
        self.assertFalse(server_cache.has("nope"))

    def test_set_overwrites_existing(self):
        server_cache.set("k", 1)
        server_cache.set("k", 2)
        self.assertEqual(server_cache.get("k"), 2)

    # ------------------------------------------------------------------
    # Missing key behavior
    # ------------------------------------------------------------------

    def test_get_missing_raises_prevent_update(self):
        with self.assertRaises(PreventUpdate):
            server_cache.get("missing")

    def test_lookup_missing_returns_default(self):
        self.assertIsNone(server_cache.lookup("missing"))

    def test_lookup_missing_returns_custom_default(self):
        sentinel = object()
        self.assertIs(server_cache.lookup("missing", default=sentinel), sentinel)

    # ------------------------------------------------------------------
    # Sentinel: distinguish missing vs stored None
    # ------------------------------------------------------------------

    def test_cache_none_value(self):
        server_cache.set("nullable", None)
        self.assertTrue(server_cache.has("nullable"))
        self.assertIsNone(server_cache.get("nullable"))

    def test_cache_none_via_lookup(self):
        server_cache.set("nullable", None)
        self.assertIsNone(server_cache.lookup("nullable"))

    def test_cache_false_value(self):
        server_cache.set("falsy", False)
        self.assertIs(server_cache.get("falsy"), False)

    def test_cache_zero_value(self):
        server_cache.set("zero", 0)
        self.assertEqual(server_cache.get("zero"), 0)

    def test_cache_empty_string(self):
        server_cache.set("empty", "")
        self.assertEqual(server_cache.get("empty"), "")

    # ------------------------------------------------------------------
    # Factory / auto-populate
    # ------------------------------------------------------------------

    def test_factory_populates_on_miss(self):
        server_cache.register("auto", lambda: "loaded")
        self.assertEqual(server_cache.get("auto"), "loaded")
        # Should be cached now
        self.assertTrue(server_cache.has("auto"))

    def test_factory_returning_none_is_cached(self):
        server_cache.register("none_factory", lambda: None)
        self.assertIsNone(server_cache.get("none_factory"))
        self.assertTrue(server_cache.has("none_factory"))

    def test_factory_not_called_if_value_present(self):
        call_count = {"n": 0}

        def factory():
            call_count["n"] += 1
            return "fresh"

        server_cache.register("k", factory)
        server_cache.set("k", "existing")
        self.assertEqual(server_cache.get("k"), "existing")
        self.assertEqual(call_count["n"], 0)

    def test_factory_failure_raises_prevent_update(self):
        server_cache.register("fail", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        with self.assertRaises(PreventUpdate):
            server_cache.get("fail")

    def test_factory_failure_returns_default_via_lookup(self):
        server_cache.register("fail", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        self.assertIsNone(server_cache.lookup("fail"))

    def test_factory_sets_multiple_keys(self):
        """Factory that populates sibling keys (like _load_func_econ_group)."""
        def group_loader():
            server_cache.set("a", 10)
            server_cache.set("b", 20)
            return 10

        server_cache.register("a", group_loader)
        self.assertEqual(server_cache.get("a"), 10)
        self.assertTrue(server_cache.has("b"))
        self.assertEqual(server_cache.get("b"), 20)

    # ------------------------------------------------------------------
    # Thread safety
    # ------------------------------------------------------------------

    def test_concurrent_get_only_loads_once(self):
        """Two threads miss the same key; only one should call the factory."""
        call_count = {"n": 0}

        def slow_factory():
            call_count["n"] += 1
            time.sleep(0.2)
            return "value"

        server_cache.register("slow", slow_factory)
        results = {}

        def getter(name):
            results[name] = server_cache.get("slow")

        t1 = threading.Thread(target=getter, args=("t1",))
        t2 = threading.Thread(target=getter, args=("t2",))
        t1.start()
        time.sleep(0.05)  # ensure t1 enters factory first
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        self.assertEqual(results["t1"], "value")
        self.assertEqual(results["t2"], "value")
        self.assertEqual(call_count["n"], 1, "Factory should be called exactly once")

    # ------------------------------------------------------------------
    # Mutation safety (defensive copies)
    # ------------------------------------------------------------------

    def test_dict_returned_is_copy(self):
        """Mutating a returned dict must not affect the cache."""
        original = {"data": [1, 2, 3]}
        server_cache.set("ref", original)
        retrieved = server_cache.get("ref")
        self.assertIsNot(retrieved, original)

        retrieved["data"].append(4)
        self.assertEqual(server_cache.get("ref")["data"], [1, 2, 3])

    def test_dataframe_returned_is_copy(self):
        """Mutating a returned DataFrame must not affect the cache."""
        import pandas as pd
        original = pd.DataFrame({"a": [1, 2, 3]})
        server_cache.set("df", original)
        retrieved = server_cache.get("df")

        retrieved["b"] = [4, 5, 6]
        self.assertNotIn("b", server_cache.get("df").columns)

    def test_immutable_returned_as_is(self):
        """Strings, numbers, etc. don't need copying."""
        server_cache.set("s", "hello")
        self.assertEqual(server_cache.get("s"), "hello")


if __name__ == "__main__":
    unittest.main()
