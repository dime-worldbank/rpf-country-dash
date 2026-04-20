import unittest
import threading
import time
from dash.exceptions import PreventUpdate
import server_store
import data_mapping


class TestServerStore(unittest.TestCase):
    """Tests for server_store module."""

    def setUp(self):
        """Reset store state between tests."""
        server_store._store.clear()
        self._saved_mapping = data_mapping.function_data_mapping.copy()
        data_mapping.function_data_mapping.clear()

    def tearDown(self):
        data_mapping.function_data_mapping.clear()
        data_mapping.function_data_mapping.update(self._saved_mapping)

    # ------------------------------------------------------------------
    # Basic get/set/has
    # ------------------------------------------------------------------

    def test_set_and_get(self):
        server_store.set("k", "v")
        self.assertEqual(server_store.get("k"), "v")

    def test_has_returns_true_for_existing_key(self):
        server_store.set("k", 42)
        self.assertTrue(server_store.has("k"))

    def test_has_returns_false_for_missing_key(self):
        self.assertFalse(server_store.has("nope"))

    def test_set_overwrites_existing(self):
        server_store.set("k", 1)
        server_store.set("k", 2)
        self.assertEqual(server_store.get("k"), 2)

    # ------------------------------------------------------------------
    # Missing key behavior
    # ------------------------------------------------------------------

    def test_get_missing_raises_prevent_update(self):
        with self.assertRaises(PreventUpdate):
            server_store.get("missing")

    def test_lookup_missing_returns_default(self):
        self.assertIsNone(server_store.lookup("missing"))

    def test_lookup_missing_returns_custom_default(self):
        sentinel = object()
        self.assertIs(server_store.lookup("missing", default=sentinel), sentinel)

    # ------------------------------------------------------------------
    # Sentinel: distinguish missing vs stored None
    # ------------------------------------------------------------------

    def test_cache_none_value(self):
        server_store.set("nullable", None)
        self.assertTrue(server_store.has("nullable"))
        self.assertIsNone(server_store.get("nullable"))

    def test_cache_none_via_lookup(self):
        server_store.set("nullable", None)
        self.assertIsNone(server_store.lookup("nullable"))

    def test_cache_false_value(self):
        server_store.set("falsy", False)
        self.assertIs(server_store.get("falsy"), False)

    def test_cache_zero_value(self):
        server_store.set("zero", 0)
        self.assertEqual(server_store.get("zero"), 0)

    def test_cache_empty_string(self):
        server_store.set("empty", "")
        self.assertEqual(server_store.get("empty"), "")

    # ------------------------------------------------------------------
    # Loader / auto-populate
    # ------------------------------------------------------------------

    def test_loader_populates_on_miss(self):
        data_mapping.function_data_mapping["auto"] = lambda: "loaded"
        self.assertEqual(server_store.get("auto"), "loaded")
        # Should be cached now
        self.assertTrue(server_store.has("auto"))

    def test_loader_returning_none_is_cached(self):
        data_mapping.function_data_mapping["none_loader"] = lambda: None
        self.assertIsNone(server_store.get("none_loader"))
        self.assertTrue(server_store.has("none_loader"))

    def test_loader_not_called_if_value_present(self):
        call_count = {"n": 0}

        def loader():
            call_count["n"] += 1
            return "fresh"

        data_mapping.function_data_mapping["k"] = loader
        server_store.set("k", "existing")
        self.assertEqual(server_store.get("k"), "existing")
        self.assertEqual(call_count["n"], 0)

    def test_loader_failure_raises_prevent_update(self):
        data_mapping.function_data_mapping["fail"] = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        with self.assertRaises(PreventUpdate):
            server_store.get("fail")

    def test_loader_failure_returns_default_via_lookup(self):
        data_mapping.function_data_mapping["fail"] = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        self.assertIsNone(server_store.lookup("fail"))

    def test_loader_sets_multiple_keys(self):
        """Loader that populates sibling keys (like _load_func_econ_group)."""
        def group_loader():
            server_store.set("a", 10)
            server_store.set("b", 20)
            return 10

        data_mapping.function_data_mapping["a"] = group_loader
        self.assertEqual(server_store.get("a"), 10)
        self.assertTrue(server_store.has("b"))
        self.assertEqual(server_store.get("b"), 20)

    # ------------------------------------------------------------------
    # Thread safety
    # ------------------------------------------------------------------

    def test_concurrent_get_returns_consistent_value(self):
        """Two threads miss the same key concurrently; both must observe the
        same cached value. The factory may run more than once — we accept
        duplicate loads in exchange for simpler coordination — but the first
        write to land wins and subsequent callers read it back.
        """
        call_count = {"n": 0}

        def slow_loader():
            call_count["n"] += 1
            time.sleep(0.2)
            return object()  # unique per call, so identity distinguishes writers

        data_mapping.function_data_mapping["slow"] = slow_loader
        results = {}

        def getter(name):
            results[name] = server_store.get("slow")

        t1 = threading.Thread(target=getter, args=("t1",))
        t2 = threading.Thread(target=getter, args=("t2",))
        t1.start()
        time.sleep(0.05)  # ensure t1 enters factory first
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        self.assertIs(
            results["t1"], results["t2"],
            "Concurrent callers must observe the same cached object",
        )
        self.assertGreaterEqual(call_count["n"], 1)
        self.assertLessEqual(call_count["n"], 2)

    # ------------------------------------------------------------------
    # Mutation safety (defensive copies)
    # ------------------------------------------------------------------

    def test_dict_returned_is_copy(self):
        """Mutating a returned dict must not affect the cache."""
        original = {"data": [1, 2, 3]}
        server_store.set("ref", original)
        retrieved = server_store.get("ref")
        self.assertIsNot(retrieved, original)

        retrieved["data"].append(4)
        self.assertEqual(server_store.get("ref")["data"], [1, 2, 3])

    def test_dataframe_returned_is_copy(self):
        """Mutating a returned DataFrame must not affect the cache."""
        import pandas as pd
        original = pd.DataFrame({"a": [1, 2, 3]})
        server_store.set("df", original)
        retrieved = server_store.get("df")

        retrieved["b"] = [4, 5, 6]
        self.assertNotIn("b", server_store.get("df").columns)

    def test_immutable_returned_as_is(self):
        """Strings, numbers, etc. don't need copying."""
        server_store.set("s", "hello")
        self.assertEqual(server_store.get("s"), "hello")


if __name__ == "__main__":
    unittest.main()
