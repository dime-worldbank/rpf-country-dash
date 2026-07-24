import unittest

from components.year_slider import (
    get_slider_config,
    YEAR_COMPLETE_STYLE,
    YEAR_PARTIAL_STYLE,
)


class TestGetSliderConfig(unittest.TestCase):
    """The subnational slider clamps to START_YEAR and spans the union of the
    spending and outcome years, styling single-dataset years as incomplete."""

    def test_clamps_years_below_start_year(self):
        # 2009 spending exists in raw data but the charts start at 2010.
        _, marks, _, min_year, _, _ = get_slider_config([2009, 2010, 2011], [2010, 2011])
        self.assertNotIn("2009", marks)
        self.assertEqual(min_year, 2010)

    def test_outcome_only_year_shown_as_incomplete(self):
        # Mozambique-like: poverty has 2023 (no spending) and pre-2010 surveys.
        expenditure = list(range(2009, 2023))  # 2009..2022
        poverty = [2002, 2008, 2014, 2019, 2022, 2023]
        _, marks, selected, min_year, max_year, _ = get_slider_config(expenditure, poverty)

        self.assertNotIn("2009", marks)                                # clamped away
        self.assertIn("2023", marks)                                   # outcome-only, still shown
        self.assertEqual(marks["2023"]["style"], YEAR_PARTIAL_STYLE)   # incomplete (no spending)
        self.assertEqual(marks["2010"]["style"], YEAR_PARTIAL_STYLE)   # incomplete (no poverty)
        self.assertEqual(marks["2014"]["style"], YEAR_COMPLETE_STYLE)  # both present
        self.assertEqual(min_year, 2010)
        self.assertEqual(max_year, 2023)
        self.assertEqual(selected, 2022)                               # latest complete year

    def test_no_overlap_defaults_to_latest_expenditure_year(self):
        # If there is no overlap, default to the latest expenditure year (not an outcome-only max).
        _, marks, selected, min_year, max_year, _ = get_slider_config([2010, 2011], [2014])
        self.assertEqual(min_year, 2010)
        self.assertEqual(max_year, 2014)
        self.assertEqual(selected, 2011)
        self.assertEqual(marks["2014"]["style"], YEAR_PARTIAL_STYLE)

    def test_outcome_subset_of_expenditure_unchanged(self):
        # edu/health slider: outcome years are a subset of (already-clamped) spending.
        _, marks, selected, min_year, max_year, _ = get_slider_config(
            [2015, 2016, 2017, 2018], [2016, 2018]
        )
        self.assertEqual(sorted(marks), ["2015", "2016", "2017", "2018"])
        self.assertEqual(marks["2016"]["style"], YEAR_COMPLETE_STYLE)
        self.assertEqual(marks["2015"]["style"], YEAR_PARTIAL_STYLE)
        self.assertEqual((min_year, max_year, selected), (2015, 2018, 2018))

    def test_no_expenditure_returns_disabled_slider(self):
        style, _, _, _, _, tooltip = get_slider_config([], [2015])
        self.assertEqual(style.get("pointer-events"), "none")
        self.assertTrue(tooltip.get("always_visible"))
