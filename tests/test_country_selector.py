import unittest

import dash_bootstrap_components as dbc
from dash import html

from components.country_selector import country_select_style, country_selector


class CountrySelectorTest(unittest.TestCase):

    def _select(self, parts):
        return next(p for p in parts if isinstance(p, dbc.Select))

    def test_single_configured_country_hides_selector_and_its_separator(self):
        parts = country_selector(["Togo"])

        select = self._select(parts)
        self.assertEqual(select.id, "country-select")
        self.assertEqual(select.style, {"display": "none"})
        self.assertEqual(sum(isinstance(p, html.Hr) for p in parts), 0)

    def test_several_or_no_configured_countries_show_selector(self):
        for countries in ([], ["Togo", "Kenya"]):
            with self.subTest(countries=countries):
                parts = country_selector(countries)
                self.assertIsNone(getattr(self._select(parts), "style", None))
                self.assertEqual(sum(isinstance(p, html.Hr) for p in parts), 1)


class CountrySelectStyleTest(unittest.TestCase):

    def test_single_configured_country_found_in_the_data_stays_hidden(self):
        self.assertEqual(country_select_style(["Togo"], ["Togo"]), {"display": "none"})

    def test_single_configured_country_missing_from_the_data_shows_the_no_data_message(self):
        for available in ([], None, ["Kenya"]):
            with self.subTest(available=available):
                self.assertEqual(country_select_style(["Togo"], available), {})

    def test_several_or_no_configured_countries_stay_visible(self):
        for configured in ([], ["Togo", "Kenya"]):
            with self.subTest(configured=configured):
                self.assertEqual(country_select_style(configured, ["Togo", "Kenya"]), {})


if __name__ == "__main__":
    unittest.main()
