"""END_YEAR caps the charts of executed spending, not those of the budget alone."""

import unittest
from unittest.mock import patch

import pandas as pd

from constants import END_YEAR
from components import budget_funding_execution, budget_increment_analysis
import data_mapping

OPEN_YEAR = END_YEAR + 1  # budget voted, accounts not closed
YEARS = [END_YEAR - 2, END_YEAR - 1, END_YEAR, OPEN_YEAR]


def _years_plotted(fig):
    return {int(x) for trace in fig.data for x in (trace.x if trace.x is not None else [])
            if x is not None}


def _national(open_year_deflated=False):
    # Real terms come from the expenditure deflator, unknown for the open year
    # unless open_year_deflated.
    df = pd.DataFrame({
        "country_name": "Togo",
        "year": YEARS,
        "budget": [100.0, 110.0, 120.0, 130.0],
        "foreign_funded_budget": [20.0, 22.0, 24.0, 26.0],
        "expenditure": [90.0, 100.0, 115.0, 40.0],
        "real_expenditure": [81.0, 90.0, 103.5, 36.0 if open_year_deflated else None],
    })
    return data_mapping._add_real_funding_split_columns(df)


def _by_function(deflated_in_open_year=()):
    rows = [
        {"country_name": "Togo", "func": func, "year": year, "budget": base + 10 * i,
         "domestic_funded_budget": base + 10 * i,
         "real_domestic_funded_budget": (
             None if year == OPEN_YEAR and func not in deflated_in_open_year
             else 0.9 * (base + 10 * i))}
        for func, base in (("Education", 100.0), ("Health", 50.0))
        for i, year in enumerate(YEARS)
    ]
    return pd.DataFrame(rows)


def _funding_store(national):
    return {"expenditure_w_poverty": national,
            "basic_country_info": {"Togo": {"currency_code": "XOF"}}}.__getitem__


class EndYearScopeTest(unittest.TestCase):
    def setUp(self):
        budget_funding_execution.clear_cache()

    @patch("components.budget_funding_execution.get_segment_narrative_i18n", return_value="")
    @patch("components.budget_funding_execution.server_store.get")
    def test_funding_sources_show_the_open_year(self, mock_get, _trend):
        mock_get.side_effect = _funding_store(_national())
        fig, _ = budget_funding_execution.render_funding("Togo", "en", "nominal")
        self.assertIn(OPEN_YEAR, _years_plotted(fig))

    @patch("components.budget_funding_execution.get_segment_narrative_i18n", return_value="")
    @patch("components.budget_funding_execution.server_store.get")
    def test_real_funding_leaves_out_an_open_year_without_deflator(self, mock_get, _trend):
        mock_get.side_effect = _funding_store(_national())
        fig, _ = budget_funding_execution.render_funding("Togo", "en", "real")
        self.assertEqual(_years_plotted(fig), set(YEARS[:-1]))

    @patch("components.budget_funding_execution.get_segment_narrative_i18n", return_value="")
    @patch("components.budget_funding_execution.server_store.get")
    def test_real_funding_shows_an_open_year_with_deflator(self, mock_get, _trend):
        mock_get.side_effect = _funding_store(_national(open_year_deflated=True))
        fig, _ = budget_funding_execution.render_funding("Togo", "en", "real")
        self.assertIn(OPEN_YEAR, _years_plotted(fig))

    @patch("components.budget_funding_execution.server_store.get")
    def test_execution_stops_at_end_year(self, mock_get):
        mock_get.side_effect = {"expenditure_w_poverty": _national()}.__getitem__
        fig = budget_funding_execution.render_execution_figure("Togo", "en")
        years = _years_plotted(fig)
        self.assertIn(END_YEAR, years)
        self.assertNotIn(OPEN_YEAR, years)

    @patch("components.budget_increment_analysis.server_store.get")
    def test_budget_changes_show_the_open_year(self, mock_get):
        mock_get.side_effect = {"func_by_country_year": _by_function()}.__getitem__
        fig, _ = budget_increment_analysis.render_fig_and_narrative(
            True, "Togo", "domestic_funded_budget", "en")
        self.assertIn(OPEN_YEAR, _years_plotted(fig))

    @patch("components.budget_increment_analysis.server_store.get")
    def test_real_budget_changes_end_at_the_last_deflated_year(self, mock_get):
        mock_get.side_effect = {"func_by_country_year": _by_function()}.__getitem__
        fig, narrative = budget_increment_analysis.render_fig_and_narrative(
            True, "Togo", "real_domestic_funded_budget", "en")
        self.assertNotIn(OPEN_YEAR, _years_plotted(fig))
        self.assertNotIn("-100", narrative)

    @patch("components.budget_increment_analysis.server_store.get")
    def test_real_budget_changes_leave_out_an_open_year_deflated_for_some_functions(self, mock_get):
        # The overall budget of that year would sum Education alone.
        mock_get.side_effect = {"func_by_country_year": _by_function({"Education"})}.__getitem__
        fig, _ = budget_increment_analysis.render_fig_and_narrative(
            True, "Togo", "real_domestic_funded_budget", "en")
        self.assertNotIn(OPEN_YEAR, _years_plotted(fig))


if __name__ == "__main__":
    unittest.main()
