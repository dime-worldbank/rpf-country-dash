import unittest
from unittest.mock import patch

import pandas as pd

from components import funding_source


class TestPrepareFundingDf(unittest.TestCase):
    """The domestic/foreign split derived from budget columns."""

    @patch("components.funding_source.server_store.get")
    def test_computes_domestic_split_and_share(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo", "Togo"],
                "year": [2018, 2019],
                "budget": [100.0, 200.0],
                "foreign_funded_budget": [30.0, 40.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        # Sorted ascending by year, domestic = budget - foreign.
        self.assertEqual(result["year"].tolist(), [2018, 2019])
        self.assertEqual(result["domestic_funded_budget"].tolist(), [70.0, 160.0])
        self.assertEqual(result["domestic_share"].tolist(), [70.0, 80.0])

    @patch("components.funding_source.server_store.get")
    def test_keeps_null_foreign_years_drops_zero_budget(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo", "Togo", "Togo", "Kenya"],
                "year": [2018, 2019, 2020, 2018],
                "budget": [100.0, 100.0, 0.0, 100.0],
                # 2019 has no breakdown; 2020 has a zero budget.
                "foreign_funded_budget": [30.0, None, 10.0, 50.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        # Zero-budget and the other country drop; the null-foreign year stays so
        # the total-budget line still shows, but its split is NaN.
        self.assertEqual(result["year"].tolist(), [2018, 2019])
        self.assertEqual(result.loc[result.year == 2018, "domestic_share"].iloc[0], 70.0)
        self.assertTrue(pd.isna(result.loc[result.year == 2019, "domestic_share"].iloc[0]))

    @patch("components.funding_source.server_store.get")
    def test_missing_foreign_column_keeps_total_budget(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo"],
                "year": [2018],
                "budget": [100.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        self.assertEqual(result["budget"].tolist(), [100.0])
        self.assertTrue(result["domestic_share"].isna().all())


class TestRealBudgetColumn(unittest.TestCase):
    """The inflation-adjusted total budget derived via the expenditure deflator."""

    @patch("components.funding_source.server_store.get")
    def test_real_budget_deflates_whole_budget(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo", "Togo"],
                "year": [2018, 2019],
                "budget": [100.0, 200.0],
                "foreign_funded_budget": [30.0, 40.0],
                "expenditure": [100.0, 100.0],
                "real_expenditure": [90.0, 80.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        self.assertEqual(result["real_budget"].tolist(), [90.0, 160.0])

    @patch("components.funding_source.server_store.get")
    def test_real_budget_is_nan_without_deflator_columns(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo"],
                "year": [2018],
                "budget": [100.0],
                "foreign_funded_budget": [30.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        self.assertTrue(result["real_budget"].isna().all())

    @patch("components.funding_source.server_store.get")
    def test_real_bars_reconcile_with_real_total(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo", "Togo"],
                "year": [2018, 2019],
                "budget": [100.0, 200.0],
                "foreign_funded_budget": [30.0, 40.0],
                "expenditure": [100.0, 100.0],
                "real_expenditure": [90.0, 80.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        recomposed = (
            result["real_domestic_funded_budget"] + result["real_foreign_funded_budget"]
        )
        self.assertEqual(recomposed.tolist(), result["real_budget"].tolist())

    @patch("components.funding_source.server_store.get")
    def test_real_budget_nan_when_expenditure_zero(self, mock_get):
        # Zero expenditure must guard to NaN, not inf.
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo"],
                "year": [2018],
                "budget": [100.0],
                "foreign_funded_budget": [30.0],
                "expenditure": [0.0],
                "real_expenditure": [0.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        self.assertTrue(result["real_budget"].isna().all())


class TestFundingSourceFigure(unittest.TestCase):
    """Two share bars plus a total-budget line on a secondary axis."""

    def _df(self):
        return pd.DataFrame(
            {
                "year": [2018, 2019],
                "budget": [100.0, 200.0],
                "foreign_funded_budget": [30.0, 40.0],
                "domestic_funded_budget": [70.0, 160.0],
                "domestic_share": [70.0, 80.0],
                "foreign_share": [30.0, 20.0],
                "real_budget": [90.0, 160.0],
                "real_domestic_funded_budget": [63.0, 128.0],
                "real_foreign_funded_budget": [27.0, 32.0],
            }
        )

    def test_domestic_bar_uses_non_blue_colour(self):
        # Domestic must stay off the central-government blue used just above.
        fig = funding_source.create_funding_source_figure(self._df(), "XOF", lang="en")

        self.assertEqual(fig.data[0].marker.color, funding_source.DOMESTIC_FUNDED_COLOR)
        self.assertNotEqual(funding_source.DOMESTIC_FUNDED_COLOR, "rgb(17, 141, 255)")

    def test_has_total_line_on_secondary_axis(self):
        fig = funding_source.create_funding_source_figure(self._df(), "XOF", lang="en")

        self.assertEqual(len(fig.data), 3)
        line = fig.data[2]
        self.assertEqual(line.type, "scatter")
        self.assertEqual(line.yaxis, "y2")

    def test_amount_switches_line_between_nominal_and_real(self):
        nominal = funding_source.create_funding_source_figure(
            self._df(), "XOF", lang="en", budget_terms="nominal"
        )
        real = funding_source.create_funding_source_figure(
            self._df(), "XOF", lang="en", budget_terms="real"
        )

        self.assertEqual(list(nominal.data[2].y), [100.0, 200.0])
        self.assertEqual(list(real.data[2].y), [90.0, 160.0])

    def test_real_mode_deflates_bar_amounts_but_keeps_shares(self):
        nominal = funding_source.create_funding_source_figure(
            self._df(), "XOF", lang="en", budget_terms="nominal"
        )
        real = funding_source.create_funding_source_figure(
            self._df(), "XOF", lang="en", budget_terms="real"
        )

        self.assertEqual(list(nominal.data[0].y), list(real.data[0].y))
        self.assertNotEqual(
            list(nominal.data[0].customdata[:, 0]),
            list(real.data[0].customdata[:, 0]),
        )

    def _df_no_split(self):
        na = [None, None]
        return pd.DataFrame(
            {
                "year": [2018, 2019],
                "budget": [100.0, 200.0],
                "foreign_funded_budget": na,
                "domestic_funded_budget": na,
                "domestic_share": na,
                "foreign_share": na,
                "real_budget": [90.0, 160.0],
                "real_domestic_funded_budget": na,
                "real_foreign_funded_budget": na,
            }
        )

    def test_split_present_titles_the_funding_question(self):
        fig = funding_source.create_funding_source_figure(self._df(), "XOF", lang="en")

        self.assertEqual(len(fig.data), 3)  # two bars + line
        self.assertIn("funded", fig.layout.title.text.lower())
        self.assertEqual(fig.layout.yaxis2.overlaying, "y")

    def test_no_split_shows_only_total_line_with_total_title(self):
        fig = funding_source.create_funding_source_figure(
            self._df_no_split(), "XOF", lang="en"
        )

        self.assertEqual(len(fig.data), 1)  # line only, no bars
        self.assertEqual(fig.data[0].type, "scatter")
        self.assertIn("total budget", fig.layout.title.text.lower())
        self.assertNotIn("yaxis2", fig.layout.to_plotly_json())


class TestFundingSourceNarrative(unittest.TestCase):
    """Total-budget trend followed by the plain funding-split average."""

    def _df(self, years, budgets, shares):
        return pd.DataFrame(
            {"year": years, "budget": budgets, "domestic_share": shares}
        )

    def test_single_point_returns_average_only(self):
        # One year can't support a trend fit, so only the split average.
        text = funding_source.format_funding_source_narrative(
            self._df([2018], [100.0], [70.0]), "Togo", lang="en"
        )

        self.assertIsInstance(text, str)
        self.assertIn("70.0%", text)
        self.assertIn("30.0%", text)

    @patch("components.funding_source.get_segment_narrative_i18n")
    def test_total_budget_trend_precedes_split_average(self, mock_trend):
        mock_trend.return_value = "the total budget grew steadily"

        result = funding_source.format_funding_source_narrative(
            self._df([2018, 2019, 2020], [100.0, 120.0, 150.0], [80.0, 75.0, 70.0]),
            "Togo",
            lang="en",
        )

        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("The total budget grew steadily"))
        self.assertIn("75.0%", result)  # mean domestic share

    @patch("components.funding_source.get_segment_narrative_i18n")
    @patch("components.funding_source.InsightExtractor")
    def test_trend_runs_on_budget_not_share(self, mock_extractor, mock_trend):
        mock_trend.return_value = "trend"

        funding_source.format_funding_source_narrative(
            self._df([2018, 2019, 2020], [100.0, 120.0, 150.0], [80.0, 75.0, 70.0]),
            "Togo",
            lang="en",
        )

        passed_values = list(mock_extractor.call_args[0][1])
        self.assertEqual(passed_values, [100.0, 120.0, 150.0])

    @patch("components.funding_source.get_segment_narrative_i18n")
    @patch("components.funding_source.InsightExtractor")
    def test_real_amount_trends_real_budget(self, mock_extractor, mock_trend):
        mock_trend.return_value = "trend"
        df = pd.DataFrame(
            {
                "year": [2018, 2019, 2020],
                "budget": [100.0, 120.0, 150.0],
                "real_budget": [95.0, 110.0, 130.0],
                "domestic_share": [80.0, 75.0, 70.0],
            }
        )

        funding_source.format_funding_source_narrative(
            df, "Togo", lang="en", budget_terms="real"
        )

        passed_values = list(mock_extractor.call_args[0][1])
        self.assertEqual(passed_values, [95.0, 110.0, 130.0])

    @patch("components.funding_source.get_segment_narrative_i18n")
    def test_falls_back_to_average_when_no_trend(self, mock_trend):
        mock_trend.return_value = ""

        result = funding_source.format_funding_source_narrative(
            self._df([2018, 2019, 2020], [100.0, 120.0, 150.0], [80.0, 75.0, 70.0]),
            "Togo",
            lang="en",
        )

        self.assertIsInstance(result, str)
        self.assertIn("75.0%", result)

    @patch("components.funding_source.get_segment_narrative_i18n")
    def test_no_split_states_breakdown_unavailable(self, mock_trend):
        mock_trend.return_value = "the total budget grew"

        result = funding_source.format_funding_source_narrative(
            self._df([2018, 2019, 2020], [100.0, 120.0, 150.0], [None, None, None]),
            "Togo",
            lang="en",
        )

        self.assertIn("The total budget grew", result)
        self.assertIn("not available in the data", result)
        self.assertNotIn("financed", result)  # no fabricated split figure


class TestPrepareExecutionDf(unittest.TestCase):
    """Execution rate and variance derived from budget vs expenditure."""

    @patch("components.funding_source.server_store.get")
    def test_computes_rate_and_variance(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo", "Togo"],
                "year": [2018, 2019],
                "budget": [100.0, 200.0],
                "expenditure": [90.0, 150.0],
            }
        )

        result = funding_source._prepare_execution_df("Togo")

        self.assertEqual(result["execution_rate"].tolist(), [90.0, 75.0])
        self.assertEqual(result["execution_variance"].tolist(), [-10.0, -25.0])

    @patch("components.funding_source.server_store.get")
    def test_excludes_null_expenditure_and_zero_budget(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo", "Togo", "Togo"],
                "year": [2018, 2019, 2020],
                "budget": [100.0, 100.0, 0.0],
                "expenditure": [90.0, None, 10.0],
            }
        )

        result = funding_source._prepare_execution_df("Togo")

        self.assertEqual(result["year"].tolist(), [2018])

    @patch("components.funding_source.server_store.get")
    def test_missing_expenditure_column_returns_empty(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {"country_name": ["Togo"], "year": [2018], "budget": [100.0]}
        )

        result = funding_source._prepare_execution_df("Togo")

        self.assertTrue(result.empty)


class TestExecutionFigure(unittest.TestCase):
    """Execution bars, coloured by metric."""

    def _df(self):
        return pd.DataFrame(
            {
                "year": [2018, 2019, 2020],
                "execution_rate": [90.0, 110.0, 75.0],
                "execution_variance": [-10.0, 10.0, -25.0],
            }
        )

    def test_rate_mode_is_single_colour_with_100_reference(self):
        fig = funding_source.create_execution_figure(self._df(), lang="en")

        self.assertEqual(list(fig.data[0].y), [90.0, 110.0, 75.0])
        self.assertEqual(fig.data[0].marker.color, funding_source.EXECUTED_COLOR)
        self.assertEqual(fig.layout.shapes[0].y0, 100)

    def test_variance_mode_colours_shortfall_red_and_zero_reference(self):
        fig = funding_source.create_execution_figure(
            self._df(), lang="en", metric="variance"
        )

        self.assertEqual(list(fig.data[0].y), [-10.0, 10.0, -25.0])
        self.assertEqual(
            list(fig.data[0].marker.color),
            [
                funding_source.SHORTFALL_COLOR,
                funding_source.EXECUTED_COLOR,
                funding_source.SHORTFALL_COLOR,
            ],
        )
        self.assertEqual(fig.layout.shapes[0].y0, 0)


class TestExecutionNarrative(unittest.TestCase):
    """The credibility-framed execution narrative built from the prepared rates."""

    def _df(self, years, rates):
        return pd.DataFrame({"year": years, "execution_rate": rates})

    def test_under_execution_leads_with_credibility(self):
        text = funding_source.format_execution_narrative(
            self._df([2018], [85.0]), "Togo", lang="en"
        )

        self.assertIsInstance(text, str)
        self.assertIn("85.0%", text)
        self.assertIn("under-executing", text)
        self.assertIn("15.0%", text)  # gap below the approved budget

    def test_on_track_execution_reads_as_credible(self):
        text = funding_source.format_execution_narrative(
            self._df([2018], [99.0]), "Togo", lang="en"
        )

        self.assertIn("credible", text)

    def test_over_execution_flags_spending_above_budget(self):
        text = funding_source.format_execution_narrative(
            self._df([2018], [108.0]), "Togo", lang="en"
        )

        self.assertIn("more than was approved", text)

    def test_lead_carries_no_date_range(self):
        # The funding paragraph states the years; execution must not repeat them.
        text = funding_source.format_execution_narrative(
            self._df([2017, 2018, 2019, 2020], [85.0, 86.0, 87.0, 88.0]),
            "Togo",
            lang="en",
        )

        self.assertNotIn("2017", text)
        self.assertNotIn("2020", text)

    def test_recent_clause_reports_rise_over_last_five_years(self):
        text = funding_source.format_execution_narrative(
            self._df(list(range(2014, 2022)), [60, 62, 64, 78, 82, 86, 90, 94]),
            "Togo",
            lang="en",
        )

        # Recent window is 2017–2021 → first is 78, not the 2014 value.
        self.assertIn("In the most recent 5 years, execution rose from 78.0% to 94.0%", text)

    def test_recent_clause_reports_fall(self):
        text = funding_source.format_execution_narrative(
            self._df([2018, 2019, 2020], [95.0, 88.0, 80.0]), "Togo", lang="en"
        )

        self.assertIn("execution fell from 95.0% to 80.0%", text)

    def test_recent_clause_reports_steady(self):
        text = funding_source.format_execution_narrative(
            self._df([2018, 2019, 2020], [90.0, 91.0, 90.5]), "Togo", lang="en"
        )

        self.assertIn("held broadly steady", text)


if __name__ == "__main__":
    unittest.main()
