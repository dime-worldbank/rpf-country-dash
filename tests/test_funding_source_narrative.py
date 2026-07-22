"""Integration tests for components.funding_source.

Drive everything through the module's public entry points (``render_funding``,
``render_execution_figure``, ``render_execution_narrative``) with realistic
``server_store``-shaped data, rather than unit-testing the private prep
helpers. Scenarios are chosen for branch coverage: split vs no-split,
national vs sector, the domestic-sentinel guard, credibility bands, and the
recent-window rise/fall/steady wording.
"""

import unittest
from unittest.mock import patch

import pandas as pd

from components import funding_source


def _rows_df(country, rows, func=None):
    df = pd.DataFrame(rows)
    df["country_name"] = country
    if func is not None:
        df["func"] = func
    return df


def _currency(country, code="XOF"):
    return {country: {"currency_code": code}}


def _store(national=None, sector=None, currency=None, func_econ=None):
    """A ``server_store.get`` stand-in keyed like the real store."""
    mapping = {}
    if national is not None:
        mapping["expenditure_w_poverty"] = national
    if sector is not None:
        mapping["func_by_country_year"] = sector
    if currency is not None:
        mapping["basic_country_info"] = currency
    if func_econ is not None:
        mapping["func_econ_raw"] = func_econ
    return mapping.__getitem__


class TestFundingSourceIntegration(unittest.TestCase):
    """render_funding: national vs sector, split vs no-split, real vs nominal."""

    def setUp(self):
        # The cache is module-global; a stale entry from another test would
        # silently mask what this test's server_store mock actually produces.
        funding_source.clear_cache()

    @patch("components.funding_source.get_segment_narrative_i18n")
    @patch("components.funding_source.server_store.get")
    def test_national_full_split(self, mock_get, mock_trend):
        mock_trend.return_value = "the budget grew steadily"
        national = _rows_df(
            "Togo",
            [
                {"year": 2018, "budget": 100.0, "foreign_funded_budget": 20.0},
                {"year": 2019, "budget": 200.0, "foreign_funded_budget": 40.0},
                {"year": 2020, "budget": 300.0, "foreign_funded_budget": 60.0},
            ],
        )
        mock_get.side_effect = _store(national=national, currency=_currency("Togo"))

        fig, narrative = funding_source.render_funding("Togo", "en", "nominal")

        self.assertEqual(len(fig.data), 3)  # domestic bar + foreign bar + total line
        self.assertEqual(fig.data[-1].name, "Total Budget")
        self.assertEqual(fig.layout.barmode, "stack")
        self.assertIsNotNone(fig.layout.yaxis2)
        self.assertTrue(narrative.startswith("The budget grew steadily"))
        self.assertIn("80.0%", narrative)  # mean domestic share
        self.assertIn("20.0%", narrative)  # mean foreign share

    @patch("components.funding_source.get_segment_narrative_i18n")
    @patch("components.funding_source.server_store.get")
    def test_national_no_split_states_unavailable(self, mock_get, mock_trend):
        mock_trend.return_value = ""  # no trend text; isolates the split branch
        national = _rows_df(
            "Kenya",
            [
                {"year": 2018, "budget": 100.0},
                {"year": 2019, "budget": 120.0},
                {"year": 2020, "budget": 150.0},
            ],
        )
        mock_get.side_effect = _store(national=national, currency=_currency("Kenya"))

        fig, narrative = funding_source.render_funding("Kenya", "en", "nominal")

        self.assertEqual(len(fig.data), 1)  # total line only, no split bars
        self.assertEqual(fig.data[0].type, "scatter")
        self.assertIn("total budget", fig.layout.title.text.lower())
        self.assertEqual(
            narrative,
            "The breakdown between domestic and foreign funding is not available in the data.",
        )

    @patch("components.funding_source.get_segment_narrative_i18n")
    @patch("components.funding_source.server_store.get")
    def test_sector_split_names_its_own_budget_and_filters_other_sectors(
        self, mock_get, mock_trend
    ):
        mock_trend.return_value = ""
        sector = _rows_df(
            "Togo",
            [
                {"year": 2018, "budget": 100.0, "domestic_funded_budget": 70.0},
                {"year": 2019, "budget": 200.0, "domestic_funded_budget": 160.0},
                # A different sector's row must never leak into the Education result.
                {"year": 2018, "budget": 999.0, "domestic_funded_budget": 500.0},
            ],
            func=["Education", "Education", "Health"],
        )
        mock_get.side_effect = _store(sector=sector, currency=_currency("Togo"))

        fig, narrative = funding_source.render_funding(
            "Togo", "en", "nominal", sector="Education"
        )

        self.assertEqual(list(fig.data[-1].x), [2018, 2019])  # Health row excluded
        self.assertEqual(fig.data[-1].name, "Education budget")
        self.assertEqual(mock_trend.call_args.kwargs["metric"], "education budget")
        self.assertIn("75.0%", narrative)  # mean domestic share: (70+80)/2

    @patch("components.funding_source.get_segment_narrative_i18n")
    @patch("components.funding_source.server_store.get")
    def test_sector_all_domestic_sentinel_is_not_a_split(self, mock_get, mock_trend):
        mock_trend.return_value = ""
        # domestic == budget is the sector table's "foreign unknown" sentinel,
        # not a genuine 100%-domestic split.
        sector = _rows_df(
            "Liberia",
            [
                {"year": 2018, "budget": 100.0, "domestic_funded_budget": 100.0},
                {"year": 2019, "budget": 200.0, "domestic_funded_budget": 200.0},
            ],
            func="Education",
        )
        mock_get.side_effect = _store(sector=sector, currency=_currency("Liberia"))

        fig, narrative = funding_source.render_funding(
            "Liberia", "en", "nominal", sector="Education"
        )

        self.assertEqual(len(fig.data), 1)  # sentinel collapses to total-only
        self.assertEqual(fig.data[0].name, "Education budget")
        self.assertIn("not available in the data", narrative)

    @patch("components.funding_source.get_segment_narrative_i18n")
    @patch("components.funding_source.server_store.get")
    def test_real_terms_deflates_the_total_line(self, mock_get, mock_trend):
        mock_trend.return_value = ""
        national = _rows_df(
            "Ghana",
            [
                {
                    "year": 2018,
                    "budget": 100.0,
                    "foreign_funded_budget": 20.0,
                    "expenditure": 100.0,
                    "real_expenditure": 90.0,
                },
                {
                    "year": 2019,
                    "budget": 200.0,
                    "foreign_funded_budget": 40.0,
                    "expenditure": 180.0,
                    "real_expenditure": 150.0,
                },
            ],
        )
        mock_get.side_effect = _store(national=national, currency=_currency("Ghana"))

        nominal_fig, _ = funding_source.render_funding("Ghana", "en", "nominal")
        real_fig, _ = funding_source.render_funding("Ghana", "en", "real")

        self.assertEqual(list(nominal_fig.data[-1].y), [100.0, 200.0])
        # deflator = real_expenditure / expenditure: 90/100, then 150/180.
        real_y = [round(v, 2) for v in real_fig.data[-1].y]
        self.assertEqual(real_y, [90.0, 166.67])
        # Shares stay the split, not the deflated amounts.
        self.assertEqual(list(nominal_fig.data[0].y), list(real_fig.data[0].y))

    @patch("components.funding_source.server_store.get")
    def test_no_data_for_country_is_unavailable(self, mock_get):
        # Data exists, but not for the requested country.
        national = _rows_df("Nigeria", [{"year": 2018, "budget": 100.0}])
        mock_get.side_effect = _store(national=national)

        fig, narrative = funding_source.render_funding("Ghana", "en", "nominal")

        self.assertEqual(len(fig.data), 0)
        self.assertEqual(narrative, "Data not available for this period.")

    @patch("components.funding_source.server_store.get")
    def test_single_year_skips_trend_but_still_reports_split(self, mock_get):
        # Real trend fitter left unmocked: a lone point must not reach it at all.
        national = _rows_df(
            "Pakistan", [{"year": 2020, "budget": 100.0, "foreign_funded_budget": 30.0}]
        )
        mock_get.side_effect = _store(national=national, currency=_currency("Pakistan"))

        _, narrative = funding_source.render_funding("Pakistan", "en", "nominal")

        self.assertIn("70.0%", narrative)
        self.assertIn("30.0%", narrative)


class TestExecutionIntegration(unittest.TestCase):
    """render_execution_figure / render_execution_narrative: credibility bands,
    the recent-window wording, sector scoping, and the variance metric."""

    def _budget_expenditure(self, country, years, rates, budget=100.0):
        rows = [
            {"year": y, "budget": budget, "expenditure": budget * r / 100.0}
            for y, r in zip(years, rates)
        ]
        return _rows_df(country, rows)

    @patch("components.funding_source.server_store.get")
    def test_under_execution_reads_as_not_credible(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Ghana", [2018], [85.0])
        )

        narrative = funding_source.render_execution_narrative("Ghana", "en")
        fig = funding_source.render_execution_figure("Ghana", "en")

        self.assertIn("under-executing", narrative)
        self.assertIn("15.0%", narrative)  # gap below the approved budget
        self.assertEqual(list(fig.data[0].y), [85.0])
        self.assertEqual(fig.data[0].marker.color, funding_source.EXECUTED_COLOR)
        self.assertEqual(fig.layout.shapes[0].y0, 100)

    @patch("components.funding_source.server_store.get")
    def test_on_track_execution_reads_as_credible(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Pakistan", [2018], [99.0])
        )

        narrative = funding_source.render_execution_narrative("Pakistan", "en")

        self.assertIn("credible", narrative)

    @patch("components.funding_source.server_store.get")
    def test_over_execution_flags_spending_above_budget(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Bangladesh", [2018], [108.0])
        )

        narrative = funding_source.render_execution_narrative("Bangladesh", "en")

        self.assertIn("more than was approved", narrative)

    @patch("components.funding_source.server_store.get")
    def test_recent_window_reports_rise_over_last_five_years(self, mock_get):
        years = list(range(2014, 2022))
        rates = [60, 62, 64, 78, 82, 86, 90, 94]
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Chile", years, rates)
        )

        narrative = funding_source.render_execution_narrative("Chile", "en")

        # Recent window is the last 5 years (2017-2021) -> starts at 78, not 60.
        self.assertIn("In the most recent 5 years, execution rose from 78.0% to 94.0%", narrative)

    @patch("components.funding_source.server_store.get")
    def test_recent_window_reports_fall(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure(
                "Uruguay", [2018, 2019, 2020], [95.0, 88.0, 80.0]
            )
        )

        narrative = funding_source.render_execution_narrative("Uruguay", "en")

        self.assertIn("execution fell from 95.0% to 80.0%", narrative)

    @patch("components.funding_source.server_store.get")
    def test_recent_window_reports_steady(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure(
                "Paraguay", [2018, 2019, 2020], [90.0, 91.0, 90.5]
            )
        )

        narrative = funding_source.render_execution_narrative("Paraguay", "en")

        self.assertIn("held broadly steady", narrative)
        self.assertIn("90.5%", narrative)

    @patch("components.funding_source.server_store.get")
    def test_sector_execution_narrative_names_the_sector_budget(self, mock_get):
        # Regression: this used to read "approved budget" for every sector,
        # not naming which budget was over/under-executing.
        sector = _rows_df(
            "Albania",
            [{"year": 2018, "budget": 100.0, "expenditure": 130.0}],
            func="Health",
        )
        func_econ = sector.assign(econ="Wage bill")
        mock_get.side_effect = _store(sector=sector, func_econ=func_econ)

        narrative = funding_source.render_execution_narrative(
            "Albania", "en", sector="Health"
        )

        self.assertIn("approved health budget", narrative)
        self.assertNotIn("approved budget,", narrative)  # not the generic form

    @patch("components.funding_source.server_store.get")
    def test_sector_scoping_excludes_other_sectors(self, mock_get):
        sector = _rows_df(
            "Togo",
            [
                {"year": 2018, "budget": 100.0, "expenditure": 90.0},
                {"year": 2018, "budget": 50.0, "expenditure": 50.0},
            ],
            func=["Education", "Health"],
        )
        mock_get.side_effect = _store(sector=sector)

        education = funding_source.render_execution_figure(
            "Togo", "en", sector="Education"
        )
        health = funding_source.render_execution_figure("Togo", "en", sector="Health")

        self.assertEqual(list(education.data[0].y), [90.0])
        self.assertEqual(list(health.data[0].y), [100.0])

    @patch("components.funding_source.server_store.get")
    def test_missing_expenditure_is_unavailable(self, mock_get):
        national = _rows_df("Colombia", [{"year": 2018, "budget": 100.0}])
        mock_get.side_effect = _store(national=national)

        fig = funding_source.render_execution_figure("Colombia", "en")
        narrative = funding_source.render_execution_narrative("Colombia", "en")

        self.assertEqual(len(fig.data), 0)
        self.assertEqual(narrative, "Data not available for this period.")

    @patch("components.funding_source.server_store.get")
    def test_variance_metric_colours_shortfall_red_with_zero_reference(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure(
                "Albania", [2018, 2019, 2020], [90.0, 110.0, 75.0]
            )
        )

        fig = funding_source.render_execution_figure("Albania", "en", metric="variance")

        self.assertEqual([round(v, 6) for v in fig.data[0].y], [-10.0, 10.0, -25.0])
        self.assertEqual(
            list(fig.data[0].marker.color),
            [
                funding_source.SHORTFALL_COLOR,
                funding_source.EXECUTED_COLOR,
                funding_source.SHORTFALL_COLOR,
            ],
        )
        self.assertEqual(fig.layout.shapes[0].y0, 0)


class TestEconExecutionBreakdown(unittest.TestCase):
    """render_econ_execution_figure / the appended high-low narrative clause."""

    def _func_econ(self, country, func, rows):
        # rows: list of (econ, year, budget, expenditure)
        return _rows_df(
            country,
            [
                {"year": y, "budget": b, "expenditure": e}
                for _, y, b, e in rows
            ],
            func=func,
        ).assign(econ=[econ for econ, _, _, _ in rows])

    @patch("components.funding_source.server_store.get")
    def test_buckets_raw_econ_categories_and_orders_traces(self, mock_get):
        func_econ = self._func_econ(
            "Albania", "Health",
            [
                ("Wage bill", 2018, 100.0, 98.0),
                ("Capital expenditures", 2018, 50.0, 20.0),
                ("Goods and services", 2018, 30.0, 45.0),
                ("Social benefits", 2018, 20.0, 18.0),  # -> "Other recurrent"
            ],
        )
        mock_get.side_effect = _store(func_econ=func_econ)

        fig = funding_source.render_econ_execution_figure(
            "Albania", "en", sector="Health"
        )

        names = [trace.name for trace in fig.data]
        self.assertEqual(names, ["Wage bill", "Capital expenditures", "Goods and services", "Other recurrent"])
        rates = {trace.name: list(trace.y) for trace in fig.data}
        self.assertEqual(rates["Wage bill"], [98.0])
        self.assertEqual(rates["Other recurrent"], [90.0])  # Social benefits bucketed in
        self.assertEqual(fig.layout.shapes[0].y0, 100)  # rate-mode reference

    @patch("components.funding_source.server_store.get")
    def test_variance_metric_uses_zero_reference(self, mock_get):
        func_econ = self._func_econ(
            "Albania", "Health", [("Wage bill", 2018, 100.0, 110.0)]
        )
        mock_get.side_effect = _store(func_econ=func_econ)

        fig = funding_source.render_econ_execution_figure(
            "Albania", "en", metric="variance", sector="Health"
        )

        self.assertEqual([round(v, 6) for v in fig.data[0].y], [10.0])
        self.assertEqual(fig.layout.shapes[0].y0, 0)

    @patch("components.funding_source.server_store.get")
    def test_no_sector_is_unavailable(self, mock_get):
        mock_get.side_effect = _store()

        fig = funding_source.render_econ_execution_figure("Albania", "en")

        self.assertEqual(len(fig.data), 0)

    @patch("components.funding_source.server_store.get")
    def test_no_data_for_sector_is_unavailable(self, mock_get):
        # Data exists, but only for a different sector.
        func_econ = self._func_econ(
            "Albania", "Education", [("Wage bill", 2018, 100.0, 98.0)]
        )
        mock_get.side_effect = _store(func_econ=func_econ)

        fig = funding_source.render_econ_execution_figure(
            "Albania", "en", sector="Health"
        )

        self.assertEqual(len(fig.data), 0)

    @patch("components.funding_source.server_store.get")
    def test_narrative_appends_highest_and_lowest_category(self, mock_get):
        func_econ = self._func_econ(
            "Albania", "Health",
            [
                ("Wage bill", 2018, 100.0, 98.0),      # 98%
                ("Capital expenditures", 2018, 50.0, 20.0),  # 40%, lowest
                ("Goods and services", 2018, 30.0, 45.0),    # 150%, highest
            ],
        )
        # render_execution_narrative also needs the sector's overall rate.
        mock_get.side_effect = _store(sector=func_econ, func_econ=func_econ)

        narrative = funding_source.render_execution_narrative(
            "Albania", "en", sector="Health"
        )

        self.assertIn("over the same period", narrative)
        self.assertIn("the goods and services category executed highest at 150.0%", narrative)
        self.assertIn("the capital expenditures category lagged at 40.0%", narrative)

    @patch("components.funding_source.server_store.get")
    def test_clause_uses_the_recent_window_not_all_time(self, mock_get):
        # Goods and services drifts from ~95% to 160% only in the last few
        # years; the clause should reflect the recent value, not the diluted
        # all-time mean (which would sit somewhere around ~113%).
        rows = []
        for year in range(2010, 2022):  # 12 years, only the last 5 (2017-2021) count
            gs_rate = 95.0 if year < 2017 else 160.0
            rows.append(("Wage bill", year, 100.0, 98.0))
            rows.append(("Goods and services", year, 100.0, gs_rate))
        func_econ = self._func_econ("Albania", "Education", rows)
        mock_get.side_effect = _store(sector=func_econ, func_econ=func_econ)

        narrative = funding_source.render_execution_narrative(
            "Albania", "en", sector="Education"
        )

        self.assertIn("the goods and services category executed highest at 160.0%", narrative)
        self.assertNotIn("113", narrative)  # would appear if it wrongly averaged all 12 years

    @patch("components.funding_source.server_store.get")
    def test_single_bucket_appends_no_clause(self, mock_get):
        func_econ = self._func_econ(
            "Albania", "Health", [("Wage bill", 2018, 100.0, 98.0)]
        )
        mock_get.side_effect = _store(sector=func_econ, func_econ=func_econ)

        narrative = funding_source.render_execution_narrative(
            "Albania", "en", sector="Health"
        )

        self.assertNotIn("category", narrative)

    @patch("components.funding_source.server_store.get")
    def test_national_narrative_never_touches_econ_breakdown(self, mock_get):
        # No "func_econ_raw" key in the store at all: if the national path
        # tried to fetch it, this would KeyError instead of returning cleanly.
        national = _rows_df(
            "Togo", [{"year": 2018, "budget": 100.0, "expenditure": 90.0}]
        )
        mock_get.side_effect = _store(national=national)

        narrative = funding_source.render_execution_narrative("Togo", "en")

        self.assertNotIn("category", narrative)


if __name__ == "__main__":
    unittest.main()
