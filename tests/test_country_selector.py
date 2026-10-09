import unittest

import dash_bootstrap_components as dbc
from dash import html

from components.country_selector import HIDDEN, country_selector, selector_styles


class CountrySelectorTest(unittest.TestCase):

    def _parts(self, countries):
        parts = country_selector(countries)
        select = next(p for p in parts if isinstance(p, dbc.Select))
        label = next(p for p in parts if getattr(p, "id", None) == "country-label")
        return parts, select, label

    def test_single_configured_country_shows_a_label_instead_of_the_dropdown(self):
        parts, select, label = self._parts(["Togo"])

        self.assertEqual(select.id, "country-select")
        self.assertEqual(select.style, HIDDEN)
        self.assertIsInstance(label, html.Div)
        self.assertEqual(label.style, {})
        self.assertEqual(sum(isinstance(p, html.Hr) for p in parts), 1)

    def test_several_or_no_configured_countries_show_the_dropdown(self):
        for countries in ([], ["Togo", "Kenya"]):
            with self.subTest(countries=countries):
                parts, select, label = self._parts(countries)
                self.assertIsNone(getattr(select, "style", None))
                self.assertEqual(label.style, HIDDEN)
                self.assertEqual(sum(isinstance(p, html.Hr) for p in parts), 1)


class SelectorStylesTest(unittest.TestCase):

    def test_single_configured_country_found_in_the_data_shows_the_label(self):
        self.assertEqual(selector_styles(["Togo"], ["Togo"]), (HIDDEN, {}))

    def test_single_configured_country_missing_from_the_data_shows_the_no_data_message(self):
        for available in ([], None, ["Kenya"]):
            with self.subTest(available=available):
                self.assertEqual(selector_styles(["Togo"], available), ({}, HIDDEN))

    def test_several_or_no_configured_countries_show_the_dropdown(self):
        for configured in ([], ["Togo", "Kenya"]):
            with self.subTest(configured=configured):
                self.assertEqual(selector_styles(configured, ["Togo", "Kenya"]), ({}, HIDDEN))


if __name__ == "__main__":
    unittest.main()
