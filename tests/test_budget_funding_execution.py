"""Integration tests for components.budget_funding_execution.

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

from components import budget_funding_execution
import data_mapping


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
        mapping["expenditure_w_poverty"] = data_mapping._add_real_funding_split_columns(national)
    if sector is not None:
        mapping["func_by_country_year"] = data_mapping._add_real_funding_split_columns(sector)
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
        budget_funding_execution.clear_cache()

    @patch("components.budget_funding_execution.get_segment_narrative_i18n")
    @patch("components.budget_funding_execution.server_store.get")
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

        fig, narrative = budget_funding_execution.render_funding("Togo", "en", "nominal")

        self.assertEqual(len(fig.data), 3)  # domestic bar + foreign bar + total line
        self.assertEqual(fig.data[-1].name, "Total Budget")
        self.assertEqual(fig.layout.barmode, "stack")
        self.assertIsNotNone(fig.layout.yaxis2)
        self.assertTrue(narrative.startswith("The budget grew steadily"))
        self.assertIn("80.0%", narrative)  # mean domestic share
        self.assertIn("20.0%", narrative)  # mean foreign share

    @patch("components.budget_funding_execution.get_segment_narrative_i18n")
    @patch("components.budget_funding_execution.server_store.get")
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

        fig, narrative = budget_funding_execution.render_funding("Kenya", "en", "nominal")

        self.assertEqual(len(fig.data), 1)  # total line only, no split bars
        self.assertEqual(fig.data[0].type, "scatter")
        self.assertIn("total budget", fig.layout.title.text.lower())
        self.assertEqual(
            narrative,
            "The breakdown between domestic and foreign funding is not available in the data.",
        )

    @patch("components.budget_funding_execution.get_segment_narrative_i18n")
    @patch("components.budget_funding_execution.server_store.get")
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

        fig, narrative = budget_funding_execution.render_funding(
            "Togo", "en", "nominal", sector="Education"
        )

        self.assertEqual(list(fig.data[-1].x), [2018, 2019])  # Health row excluded
        self.assertEqual(fig.data[-1].name, "Education budget")
        self.assertEqual(mock_trend.call_args.kwargs["metric"], "education budget")
        self.assertIn("75.0%", narrative)  # mean domestic share: (70+80)/2

    @patch("components.budget_funding_execution.get_segment_narrative_i18n")
    @patch("components.budget_funding_execution.server_store.get")
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

        fig, narrative = budget_funding_execution.render_funding(
            "Liberia", "en", "nominal", sector="Education"
        )

        self.assertEqual(len(fig.data), 1)  # sentinel collapses to total-only
        self.assertEqual(fig.data[0].name, "Education budget")
        self.assertIn("not available in the data", narrative)

    @patch("components.budget_funding_execution.get_segment_narrative_i18n")
    @patch("components.budget_funding_execution.server_store.get")
    def test_real_terms_uses_source_real_budget_for_total_line(self, mock_get, mock_trend):
        mock_trend.return_value = ""
        national = _rows_df(
            "Ghana",
            [
                {
                    "year": 2018,
                    "budget": 100.0,
                    "real_budget": 90.0,
                    "foreign_funded_budget": 20.0,
                    "expenditure": 100.0,
                    "real_expenditure": 90.0,
                },
                {
                    "year": 2019,
                    "budget": 200.0,
                    "real_budget": 166.67,
                    "foreign_funded_budget": 40.0,
                    "expenditure": 180.0,
                    "real_expenditure": 150.0,
                },
            ],
        )
        mock_get.side_effect = _store(national=national, currency=_currency("Ghana"))

        nominal_fig, _ = budget_funding_execution.render_funding("Ghana", "en", "nominal")
        real_fig, _ = budget_funding_execution.render_funding("Ghana", "en", "real")

        self.assertEqual(list(nominal_fig.data[-1].y), [100.0, 200.0])
        # Real terms should come from source ``real_budget`` directly.
        real_y = [round(v, 2) for v in real_fig.data[-1].y]
        self.assertEqual(real_y, [90.0, 166.67])
        # Shares stay the split, not the deflated amounts.
        self.assertEqual(list(nominal_fig.data[0].y), list(real_fig.data[0].y))

    @patch("components.budget_funding_execution.server_store.get")
    def test_no_data_for_country_is_unavailable(self, mock_get):
        # Data exists, but not for the requested country.
        national = _rows_df("Nigeria", [{"year": 2018, "budget": 100.0}])
        mock_get.side_effect = _store(national=national)

        fig, narrative = budget_funding_execution.render_funding("Ghana", "en", "nominal")

        self.assertEqual(len(fig.data), 0)
        self.assertEqual(narrative, "Data not available for this period.")

    @patch("components.budget_funding_execution.server_store.get")
    def test_single_year_skips_trend_but_still_reports_split(self, mock_get):
        # Real trend fitter left unmocked: a lone point must not reach it at all.
        national = _rows_df(
            "Pakistan", [{"year": 2020, "budget": 100.0, "foreign_funded_budget": 30.0}]
        )
        mock_get.side_effect = _store(national=national, currency=_currency("Pakistan"))

        _, narrative = budget_funding_execution.render_funding("Pakistan", "en", "nominal")

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

    @patch("components.budget_funding_execution.server_store.get")
    def test_under_execution_reads_as_not_credible(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Ghana", [2018], [85.0])
        )

        narrative = budget_funding_execution.render_execution_narrative("Ghana", "en")
        fig = budget_funding_execution.render_execution_figure("Ghana", "en")

        self.assertIn("under-executing", narrative)
        self.assertIn("15.0%", narrative)  # gap below the approved budget
        self.assertEqual(list(fig.data[0].y), [85.0])
        # 85% is outside B (90-110) too, so it's the C-tier color, at reduced
        # opacity so the band underneath still shows through.
        self.assertEqual(list(fig.data[0].marker.color), [budget_funding_execution.PEFA_C_COLOR])
        self.assertEqual(fig.data[0].marker.opacity, budget_funding_execution.PEFA_BAR_OPACITY)

    @patch("components.budget_funding_execution.server_store.get")
    def test_on_track_execution_reads_as_credible(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Pakistan", [2018], [99.0])
        )

        narrative = budget_funding_execution.render_execution_narrative("Pakistan", "en")

        self.assertIn("credible", narrative)

    @patch("components.budget_funding_execution.server_store.get")
    def test_over_execution_flags_spending_above_budget(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Bangladesh", [2018], [108.0])
        )

        narrative = budget_funding_execution.render_execution_narrative("Bangladesh", "en")

        self.assertIn("more than was approved", narrative)

    @patch("components.budget_funding_execution.server_store.get")
    def test_recent_window_reports_rise_over_last_five_years(self, mock_get):
        years = list(range(2014, 2022))
        rates = [60, 62, 64, 78, 82, 86, 90, 94]
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Chile", years, rates)
        )

        narrative = budget_funding_execution.render_execution_narrative("Chile", "en")

        # Recent window is the last 5 years (2017-2021) -> starts at 78, not 60.
        self.assertIn("In the most recent 5 years, execution rose from 78.0% to 94.0%", narrative)

    @patch("components.budget_funding_execution.server_store.get")
    def test_recent_window_reports_fall(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure(
                "Uruguay", [2018, 2019, 2020], [95.0, 88.0, 80.0]
            )
        )

        narrative = budget_funding_execution.render_execution_narrative("Uruguay", "en")

        self.assertIn("execution fell from 95.0% to 80.0%", narrative)

    @patch("components.budget_funding_execution.server_store.get")
    def test_recent_window_reports_steady(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure(
                "Paraguay", [2018, 2019, 2020], [90.0, 91.0, 90.5]
            )
        )

        narrative = budget_funding_execution.render_execution_narrative("Paraguay", "en")

        self.assertIn("held broadly steady", narrative)
        self.assertIn("90.5%", narrative)

    @patch("components.budget_funding_execution.server_store.get")
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

        narrative = budget_funding_execution.render_execution_narrative(
            "Albania", "en", sector="Health"
        )

        self.assertIn("approved health budget", narrative)
        self.assertNotIn("approved budget,", narrative)  # not the generic form

    @patch("components.budget_funding_execution.server_store.get")
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

        education = budget_funding_execution.render_execution_figure(
            "Togo", "en", sector="Education"
        )
        health = budget_funding_execution.render_execution_figure("Togo", "en", sector="Health")

        self.assertEqual(list(education.data[0].y), [90.0])
        self.assertEqual(list(health.data[0].y), [100.0])

    @patch("components.budget_funding_execution.server_store.get")
    def test_missing_expenditure_is_unavailable(self, mock_get):
        national = _rows_df("Colombia", [{"year": 2018, "budget": 100.0}])
        mock_get.side_effect = _store(national=national)

        fig = budget_funding_execution.render_execution_figure("Colombia", "en")
        narrative = budget_funding_execution.render_execution_narrative("Colombia", "en")

        self.assertEqual(len(fig.data), 0)
        self.assertEqual(narrative, "Data not available for this period.")

    @patch("components.budget_funding_execution.server_store.get")
    def test_execution_chart_shades_pefa_abc_bands(self, mock_get):
        mock_get.side_effect = _store(
            national=self._budget_expenditure("Ghana", [2018], [99.0])
        )

        rate_fig = budget_funding_execution.render_execution_figure("Ghana", "en")
        # 3 nested hrects (C, B, A — widest first) precede the reference hline.
        rate_bands = [
            (round(s.y0), round(s.y1), s.fillcolor) for s in rate_fig.layout.shapes[:3]
        ]
        self.assertEqual(
            rate_bands,
            [
                (85, 115, budget_funding_execution.PEFA_C_BAND_COLOR),
                (90, 110, budget_funding_execution.PEFA_B_BAND_COLOR),
                (95, 105, budget_funding_execution.PEFA_A_BAND_COLOR),
            ],
        )
        self.assertEqual(rate_fig.layout.shapes[-1].y0, 100)  # reference line at 100%

        variance_fig = budget_funding_execution.render_execution_figure(
            "Ghana", "en", metric="variance"
        )
        variance_bands = [(round(s.y0), round(s.y1)) for s in variance_fig.layout.shapes[:3]]
        self.assertEqual(variance_bands, [(-15, 15), (-10, 10), (-5, 5)])
        self.assertEqual(variance_fig.layout.shapes[-1].y0, 0)  # reference line at 0

    @patch("components.budget_funding_execution.server_store.get")
    def test_bars_colored_by_pefa_tier_at_reduced_opacity(self, mock_get):
        # 99% -> A, 92% -> B (outside A, inside B), 70% -> C (outside B too).
        mock_get.side_effect = _store(
            national=self._budget_expenditure(
                "Ghana", [2018, 2019, 2020], [99.0, 92.0, 70.0]
            )
        )

        fig = budget_funding_execution.render_execution_figure("Ghana", "en")

        self.assertEqual(
            list(fig.data[0].marker.color),
            [
                budget_funding_execution.PEFA_A_COLOR,
                budget_funding_execution.PEFA_B_COLOR,
                budget_funding_execution.PEFA_C_COLOR,
            ],
        )
        self.assertEqual(fig.data[0].marker.opacity, budget_funding_execution.PEFA_BAR_OPACITY)


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

    @patch("components.budget_funding_execution.server_store.get")
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

        fig = budget_funding_execution.render_econ_execution_figure(
            "Albania", "en", sector="Health"
        )

        names = [trace.name for trace in fig.data]
        self.assertEqual(names, ["Wage bill", "Capital expenditures", "Goods and services", "Other recurrent"])
        rates = {trace.name: list(trace.y) for trace in fig.data}
        self.assertEqual(rates["Wage bill"], [98.0])
        self.assertEqual(rates["Other recurrent"], [90.0])  # Social benefits bucketed in
        self.assertEqual(fig.layout.shapes[0].y0, 100)  # rate-mode reference

    @patch("components.budget_funding_execution.server_store.get")
    def test_variance_metric_uses_zero_reference(self, mock_get):
        func_econ = self._func_econ(
            "Albania", "Health", [("Wage bill", 2018, 100.0, 110.0)]
        )
        mock_get.side_effect = _store(func_econ=func_econ)

        fig = budget_funding_execution.render_econ_execution_figure(
            "Albania", "en", metric="variance", sector="Health"
        )

        self.assertEqual([round(v, 6) for v in fig.data[0].y], [10.0])
        self.assertEqual(fig.layout.shapes[0].y0, 0)

    @patch("components.budget_funding_execution.server_store.get")
    def test_no_sector_is_unavailable(self, mock_get):
        mock_get.side_effect = _store()

        fig = budget_funding_execution.render_econ_execution_figure("Albania", "en")

        self.assertEqual(len(fig.data), 0)

    @patch("components.budget_funding_execution.server_store.get")
    def test_no_data_for_sector_is_unavailable(self, mock_get):
        # Data exists, but only for a different sector.
        func_econ = self._func_econ(
            "Albania", "Education", [("Wage bill", 2018, 100.0, 98.0)]
        )
        mock_get.side_effect = _store(func_econ=func_econ)

        fig = budget_funding_execution.render_econ_execution_figure(
            "Albania", "en", sector="Health"
        )

        self.assertEqual(len(fig.data), 0)

    @patch("components.budget_funding_execution.server_store.get")
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

        narrative = budget_funding_execution.render_execution_narrative(
            "Albania", "en", sector="Health"
        )

        self.assertIn("over the same period", narrative)
        self.assertIn("the goods and services category executed highest on average at 150.0%", narrative)
        self.assertIn("the capital expenditures category lagged on average at 40.0%", narrative)

    @patch("components.budget_funding_execution.server_store.get")
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

        narrative = budget_funding_execution.render_execution_narrative(
            "Albania", "en", sector="Education"
        )

        self.assertIn("the goods and services category executed highest on average at 160.0%", narrative)
        self.assertNotIn("113", narrative)  # would appear if it wrongly averaged all 12 years

    @patch("components.budget_funding_execution.server_store.get")
    def test_single_bucket_appends_no_clause(self, mock_get):
        func_econ = self._func_econ(
            "Albania", "Health", [("Wage bill", 2018, 100.0, 98.0)]
        )
        mock_get.side_effect = _store(sector=func_econ, func_econ=func_econ)

        narrative = budget_funding_execution.render_execution_narrative(
            "Albania", "en", sector="Health"
        )

        self.assertNotIn("category", narrative)

    @patch("components.budget_funding_execution.server_store.get")
    def test_national_narrative_never_touches_econ_breakdown(self, mock_get):
        # No "func_econ_raw" key in the store at all: if the national path
        # tried to fetch it, this would KeyError instead of returning cleanly.
        national = _rows_df(
            "Togo", [{"year": 2018, "budget": 100.0, "expenditure": 90.0}]
        )
        mock_get.side_effect = _store(national=national)

        narrative = budget_funding_execution.render_execution_narrative("Togo", "en")

        self.assertNotIn("category", narrative)


if __name__ == "__main__":
    unittest.main()
