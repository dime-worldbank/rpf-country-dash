"""END_YEAR, the charts' display ceiling, read from the environment."""

import importlib
import os
import unittest
from unittest.mock import patch

import constants


class YearSettingTest(unittest.TestCase):
    def test_unset_or_empty_gives_default(self):
        for env in ({}, {"END_YEAR": ""}, {"END_YEAR": "  "}):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                self.assertEqual(constants.year_setting("END_YEAR", 2024), 2024)

    def test_year_is_read(self):
        with patch.dict(os.environ, {"END_YEAR": " 2025 "}):
            self.assertEqual(constants.year_setting("END_YEAR", 2024), 2025)

    def test_invalid_values_stop_with_the_variable_name(self):
        for raw, message in (("2025a", "must be a year"), ("1999", "must be 2010 or later")):
            with self.subTest(raw=raw), patch.dict(os.environ, {"END_YEAR": raw}):
                with self.assertRaisesRegex(ValueError, f"END_YEAR {message}"):
                    constants.year_setting("END_YEAR", 2024)

    def test_end_year_follows_the_environment(self):
        try:
            with patch.dict(os.environ, {"END_YEAR": "2025"}):
                self.assertEqual(importlib.reload(constants).END_YEAR, 2025)
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(importlib.reload(constants).END_YEAR, 2024)
        finally:
            importlib.reload(constants)


if __name__ == "__main__":
    unittest.main()
