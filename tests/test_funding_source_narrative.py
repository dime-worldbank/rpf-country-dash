import unittest
from unittest.mock import patch

import pandas as pd
from dash import html

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
    def test_excludes_null_foreign_and_zero_budget_years(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo", "Togo", "Togo", "Kenya"],
                "year": [2018, 2019, 2020, 2018],
                "budget": [100.0, 100.0, 0.0, 100.0],
                # 2019 has no reported breakdown; 2020 has a zero budget.
                "foreign_funded_budget": [30.0, None, 10.0, 50.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        # Only Togo 2018 survives: null-foreign and zero-budget rows drop,
        # and the other country is filtered out.
        self.assertEqual(result["year"].tolist(), [2018])

    @patch("components.funding_source.server_store.get")
    def test_missing_foreign_column_returns_empty(self, mock_get):
        mock_get.return_value = pd.DataFrame(
            {
                "country_name": ["Togo"],
                "year": [2018],
                "budget": [100.0],
            }
        )

        result = funding_source._prepare_funding_df("Togo")

        self.assertTrue(result.empty)


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
            self._df(), "XOF", lang="en", amount="nominal"
        )
        real = funding_source.create_funding_source_figure(
            self._df(), "XOF", lang="en", amount="real"
        )

        self.assertEqual(list(nominal.data[2].y), [100.0, 200.0])
        self.assertEqual(list(real.data[2].y), [90.0, 160.0])

    def test_real_mode_deflates_bar_amounts_but_keeps_shares(self):
        nominal = funding_source.create_funding_source_figure(
            self._df(), "XOF", lang="en", amount="nominal"
        )
        real = funding_source.create_funding_source_figure(
            self._df(), "XOF", lang="en", amount="real"
        )

        self.assertEqual(list(nominal.data[0].y), list(real.data[0].y))
        self.assertNotEqual(
            list(nominal.data[0].customdata[:, 0]),
            list(real.data[0].customdata[:, 0]),
        )


class TestFundingSourceNarrative(unittest.TestCase):
    """The narrative text built from the prepared split."""

    def _df(self, years, shares):
        return pd.DataFrame({"year": years, "domestic_share": shares})

    def test_single_point_returns_average_only(self):
        # One year can't support a trend fit, so only the average sentence.
        text = funding_source.format_funding_source_narrative(
            self._df([2018], [70.0]), "Togo", lang="en"
        )

        self.assertIsInstance(text, str)
        self.assertIn("70.0%", text)
        self.assertIn("30.0%", text)

    @patch("components.funding_source.get_segment_narrative_i18n")
    def test_multi_point_leads_with_trend_then_average(self, mock_trend):
        mock_trend.return_value = "the domestic share grew steadily"

        result = funding_source.format_funding_source_narrative(
            self._df([2018, 2019, 2020], [80.0, 75.0, 70.0]), "Togo", lang="en"
        )

        # Trend + <br> + average, rendered as html.P children.
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], "The domestic share grew steadily")
        self.assertIsInstance(result[1], html.Br)
        self.assertIn("75.0%", result[2])  # mean domestic share

    @patch("components.funding_source.get_segment_narrative_i18n")
    def test_multi_point_falls_back_to_average_when_no_trend(self, mock_trend):
        mock_trend.return_value = ""

        result = funding_source.format_funding_source_narrative(
            self._df([2018, 2019, 2020], [80.0, 75.0, 70.0]), "Togo", lang="en"
        )

        self.assertIsInstance(result, str)
        self.assertIn("75.0%", result)


if __name__ == "__main__":
    unittest.main()
