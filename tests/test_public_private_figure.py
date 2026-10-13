"""The household vs government charts on the education and health pages.

Years are categories on these charts: a numeric axis spreads a single year over
a range and labels fractional ticks (2020.6 ... 2021.4). Every year is a bar;
on long series only every third year is labelled.
"""

import unittest
from unittest.mock import patch

import dash
import pandas as pd

# Page modules call dash.register_page on import, which needs a pages-enabled app.
dash.Dash(__name__, use_pages=True, pages_folder="")

from pages import education, health  # noqa: E402


def _store(prefix, years):
    rows = lambda value: pd.DataFrame(
        {"country_name": "Togo", "year": years, "real_expenditure": [value] * len(years)}
    )
    return {
        "basic_country_info": {"Togo": {"currency_code": "XOF"}},
        f"{prefix}_private_expenditure": rows(51.0),
        f"{prefix}_public_expenditure": rows(49.0),
    }.get


class PublicPrivateFigureTest(unittest.TestCase):
    def _figure(self, page, prefix, years):
        with patch.object(page.server_store, "get", side_effect=_store(prefix, years)):
            fig, _ = page.render_public_private_figure(
                ["stored"], ["stored"], "Togo", {"Togo": {}}, "fr")
        return fig

    def test_single_year_is_one_category(self):
        for page, prefix in ((education, "edu"), (health, "health")):
            with self.subTest(page=page.__name__):
                fig = self._figure(page, prefix, [2021])
                self.assertEqual(fig.layout.yaxis.type, "category")
                self.assertEqual([list(trace.y) for trace in fig.data], [["2021"], ["2021"]])

    def test_several_years_run_oldest_at_the_bottom(self):
        for page, prefix in ((education, "edu"), (health, "health")):
            with self.subTest(page=page.__name__):
                fig = self._figure(page, prefix, [2017, 2021])
                self.assertEqual(fig.layout.yaxis.type, "category")
                # Category axes run upward in this order; the rows arrive newest first.
                self.assertEqual(fig.layout.yaxis.categoryorder, "category ascending")
                self.assertEqual([sorted(trace.y) for trace in fig.data], [["2017", "2021"]] * 2)

    def test_short_series_labels_every_year(self):
        for page, prefix in ((education, "edu"), (health, "health")):
            with self.subTest(page=page.__name__):
                fig = self._figure(page, prefix, [2017, 2021])
                self.assertEqual(list(fig.layout.yaxis.tickvals), ["2017", "2021"])

    def test_long_series_keeps_every_bar_but_labels_every_third_year(self):
        years = list(range(2010, 2024))
        for page, prefix in ((education, "edu"), (health, "health")):
            with self.subTest(page=page.__name__):
                fig = self._figure(page, prefix, years)
                self.assertEqual(
                    [sorted(trace.y) for trace in fig.data], [[str(y) for y in years]] * 2
                )
                self.assertEqual(
                    list(fig.layout.yaxis.tickvals), ["2011", "2014", "2017", "2020", "2023"]
                )


if __name__ == "__main__":
    unittest.main()
