import unittest
import pandas as pd
import plotly.graph_objects as go
from pandas.testing import assert_frame_equal
import math
from utils import (
    filter_country_sort_year,
    get_correlation_text,
    assess_statistical_confidence,
    calculate_cagr,
    format_currency,
    add_currency_column,
    format_currency_yaxis,
    millify,
)

class TestUtils(unittest.TestCase):

    def setUp(self):
        self.data = {
            'country_name': ['USA', 'Canada', 'USA', 'Mexico', 'USA', 'Canada'],
            'year': [1999, 2015, 2021, 2018, 2010, 2001],
            'earliest_year': [1999, 2001, 1999, 2018, 1999, 2001],
            'value': [100, 200, 300, 400, 500, 600]
        }
        self.df = pd.DataFrame(self.data)

        self.x_col = {"col_name": "x", "display": "X Variable"}
        self.y_col = {"col_name": "y", "display": "Y Variable"}

    def test_filter_by_country(self):
        # Test filtering by country "USA" and sorting
        expected_data = {
            'country_name': ['USA', 'USA', 'USA'],
            'year': [2021, 2010, 1999],
            'earliest_year': [1999, 1999, 1999],
            'value': [300, 500, 100]
        }
        expected_df = pd.DataFrame(expected_data)
        result_df = filter_country_sort_year(self.df, 'USA', start_year=0)
        assert_frame_equal(result_df.reset_index(drop=True), expected_df)

    def test_filter_no_results(self):
        # Test filtering by country not present in the dataframe
        result_df = filter_country_sort_year(self.df, 'France')
        self.assertTrue(result_df.empty)

    def test_filter_by_country_with_start_year(self):
        # Test filtering by country "Canada"
        # only keeping rows >= start & earliest_year is updated
        expected_data = {
            'country_name': ['Canada'],
            'year': [2015],
            'earliest_year': [2015],
            'value': [200]
        }
        expected_df = pd.DataFrame(expected_data)
        result_df = filter_country_sort_year(self.df, 'Canada', start_year=2010)
        assert_frame_equal(result_df.reset_index(drop=True), expected_df)

    def test_positive_strong_correlation_small_sample(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("very strong positive", result)
        self.assertIn("only 3 data points", result)
        self.assertIn("caution", result)

    def test_negative_strong_correlation_small_sample(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [-1, -2, -3]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("very strong inverse", result)
        self.assertIn("caution", result)

    def test_weak_correlation(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 2, 1.5, 3.5, 1]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertRegex(result, r"weak positive")

    def test_no_variability_x(self):
        df = pd.DataFrame({"x": [1, 1, 1], "y": [2, 3, 4]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("insufficient variability", result)

    def test_no_variability_y(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [5, 5, 5, 5, 5]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("insufficient variability", result)

    def test_insufficient_data_points(self):
        df = pd.DataFrame({"x": [1, 2], "y": [2, 4]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("insufficient data points", result)

    def test_outlier_robust(self):
        # Spearman is robust to outliers - the extreme value (100) doesn't flip the correlation
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "y": [12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 100]
        })
        result = get_correlation_text(df, self.x_col, self.y_col)
        # Rank-based correlation correctly identifies the inverse relationship
        self.assertIn("inverse relationship", result)

    def test_large_sample_significant(self):
        df = pd.DataFrame({
            "x": list(range(1, 21)),
            "y": [v * 2 + 0.1 for v in range(1, 21)]
        })
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("indicates", result)
        self.assertNotIn("not statistically significant", result)

    def test_medium_sample_not_significant(self):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5, 6, 7],
            "y": [3, 1, 4, 2, 5, 3, 4]
        })
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("not statistically significant", result)

    def test_no_apparent_correlation(self):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "y": [5, 3, 6, 4, 5, 4, 6, 3, 5, 4]
        })
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("no apparent correlation", result)

    def test_uses_spearman_robust_to_outliers(self):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 100],
            "y": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        })
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("very strong positive", result)

    def test_significant_uses_generally_associated(self):
        df = pd.DataFrame({
            "x": list(range(1, 21)),
            "y": [v * 2 for v in range(1, 21)]
        })
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("is generally associated with", result)

    def test_not_significant_uses_may_be_associated(self):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5, 6, 7],
            "y": [3, 1, 4, 2, 5, 3, 4]
        })
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("may be associated with", result)
        
    def test_cagr_invalid_years(self):
        self.assertIsNone(calculate_cagr(100, 200, None))
        self.assertIsNone(calculate_cagr(100, 200, 0))
        self.assertIsNone(calculate_cagr(100, 200, -2))

    def test_cagr_invalid_data(self):
        self.assertIsNone(calculate_cagr(None, 200, 5))
        self.assertIsNone(calculate_cagr(100, None, 5))
        self.assertIsNone(calculate_cagr(float('nan'), 200, 5))
        self.assertIsNone(calculate_cagr(0, 200, 5))
        self.assertIsNone(calculate_cagr(-100, 200, 5))


class TestAssessStatisticalConfidence(unittest.TestCase):

    def test_insufficient_data(self):
        result = assess_statistical_confidence(n=2, p_value=0.01)
        self.assertEqual(result["confidence"], "insufficient")
        self.assertEqual(result["verb"], "cannot be determined")
        self.assertIn("insufficient data points", result["caveat"])
        self.assertFalse(result["is_significant"])

    def test_low_confidence_below_correlation_threshold(self):
        result = assess_statistical_confidence(n=4, p_value=0.01)
        self.assertEqual(result["confidence"], "low")
        self.assertEqual(result["verb"], "tentatively suggests")
        self.assertIn("caution", result["caveat"])
        self.assertFalse(result["is_significant"])

    def test_low_confidence_not_significant(self):
        result = assess_statistical_confidence(n=10, p_value=0.15)
        self.assertEqual(result["confidence"], "low")
        self.assertEqual(result["verb"], "suggests")
        self.assertIn("not statistically significant", result["caveat"])
        self.assertFalse(result["is_significant"])

    def test_high_confidence_significant(self):
        result = assess_statistical_confidence(n=7, p_value=0.05)
        self.assertEqual(result["confidence"], "high")
        self.assertEqual(result["verb"], "indicates")
        self.assertIsNone(result["caveat"])
        self.assertTrue(result["is_significant"])

    def test_boundary_p_threshold(self):
        result_above = assess_statistical_confidence(n=10, p_value=0.11)
        self.assertEqual(result_above["confidence"], "low")
        self.assertFalse(result_above["is_significant"])

        result_at = assess_statistical_confidence(n=10, p_value=0.10)
        self.assertEqual(result_at["confidence"], "high")
        self.assertTrue(result_at["is_significant"])

    def test_custom_p_threshold(self):
        result = assess_statistical_confidence(n=10, p_value=0.08, p_threshold=0.05)
        self.assertEqual(result["confidence"], "low")
        self.assertFalse(result["is_significant"])

class TestFormatCurrency(unittest.TestCase):

    def test_thousands(self):
        # Bhutan: 1,000 BTN (Ngultrum) should format as "1.00 K BTN"
        result = format_currency(1000, "BTN")
        self.assertEqual(result, "1.00 K BTN")

    def test_millions(self):
        # Kenya: 1.5M KES (Shilling) — typical government budget figure
        result = format_currency(1_500_000, "KES")
        self.assertEqual(result, "1.50 M KES")

    def test_billions(self):
        # Kenya: 2B KES — national GDP scale
        result = format_currency(2_000_000_000, "KES")
        self.assertEqual(result, "2.00 B KES")

    def test_small_value(self):
        # Bhutan: 250 BTN — values under 1000 have no suffix
        result = format_currency(250, "BTN")
        self.assertEqual(result, "250.00 BTN")

    def test_zero(self):
        # Zero value edge case with Kenyan Shilling
        result = format_currency(0, "KES")
        self.assertEqual(result, "0.00 KES")

    def test_currency_code_used(self):
        # Ensure the BTN suffix appears in the output
        result = format_currency(5000, "BTN")
        self.assertTrue(result.endswith(" BTN"))



class TestAddCurrencyColumn(unittest.TestCase):

    def setUp(self):
        self.df = pd.DataFrame({
            "expenditure": [1_000, 500_000, 2_000_000_000],
            "country": ["Bhutan", "Kenya", "Kenya"]
        })

    def test_formatted_column_created(self):
        add_currency_column(self.df, "expenditure", "BTN")
        self.assertIn("expenditure_formatted", self.df.columns)

    def test_formatted_values_correct_btn(self):
        add_currency_column(self.df, "expenditure", "BTN")
        self.assertEqual(self.df["expenditure_formatted"].iloc[0], "1.00 K BTN")
        self.assertEqual(self.df["expenditure_formatted"].iloc[1], "500.00 K BTN")
        self.assertEqual(self.df["expenditure_formatted"].iloc[2], "2.00 B BTN")

    def test_formatted_values_correct_kes(self):
        add_currency_column(self.df, "expenditure", "KES")
        self.assertEqual(self.df["expenditure_formatted"].iloc[0], "1.00 K KES")
        self.assertEqual(self.df["expenditure_formatted"].iloc[1], "500.00 K KES")
        self.assertEqual(self.df["expenditure_formatted"].iloc[2], "2.00 B KES")

    def test_original_column_unchanged(self):
        add_currency_column(self.df, "expenditure", "BTN")
        self.assertEqual(self.df["expenditure"].iloc[0], 1_000)


class TestFormatCurrencyYaxis(unittest.TestCase):

    def setUp(self):
        self.fig = go.Figure()

    def test_yaxis_title_includes_currency_btn(self):
        # Bhutan Ngultrum on a GDP chart
        result = format_currency_yaxis(self.fig, "BTN", "GDP")
        self.assertEqual(result.layout.yaxis.title.text, "GDP (BTN)")

    def test_yaxis_title_includes_currency_kes(self):
        # Kenya Shilling on a government expenditure chart
        result = format_currency_yaxis(self.fig, "KES", "Government Expenditure")
        self.assertEqual(result.layout.yaxis.title.text, "Government Expenditure (KES)")

    def test_default_xaxis_tickformat(self):
        result = format_currency_yaxis(self.fig, "KES", "GDP")
        self.assertEqual(result.layout.xaxis.tickformat, "d")

    def test_custom_xaxis_tickformat(self):
        result = format_currency_yaxis(self.fig, "BTN", "GDP", x_format=".2f")
        self.assertEqual(result.layout.xaxis.tickformat, ".2f")

    def test_yaxis_is_fixed_range(self):
        result = format_currency_yaxis(self.fig, "KES", "GDP")
        self.assertTrue(result.layout.yaxis.fixedrange)

    def test_returns_figure(self):
        result = format_currency_yaxis(self.fig, "BTN", "GDP")
        self.assertIsInstance(result, go.Figure)


class TestMillify(unittest.TestCase):

    def test_nan_returns_na(self):
        result = millify(float('nan'))
        self.assertEqual(result, "N/A")

    def test_thousands(self):
        result = millify(1500)
        self.assertEqual(result, "1.50 K")

    def test_millions(self):
        result = millify(2_000_000)
        self.assertEqual(result, "2.00 M")

    def test_small_number(self):
        result = millify(750)
        self.assertEqual(result, "750.00")

    def test_zero(self):
        result = millify(0)
        self.assertEqual(result, "0.00")

    # --- French number formatting: comma decimal + long-scale suffixes ---

    def test_fr_thousands_uses_lowercase_k_and_comma(self):
        self.assertEqual(millify(1500, lang="fr"), "1,50 k")

    def test_fr_millions_same_suffix_as_en(self):
        self.assertEqual(millify(2_000_000, lang="fr"), "2,00 M")

    def test_fr_billions_uses_md_not_b(self):
        # 10^9: EN "B" would mean something different (10^18) in French
        # long-scale — so we use "Md" (milliard).
        self.assertEqual(millify(2_000_000_000, lang="fr"), "2,00 Md")

    def test_fr_trillions_uses_bn_not_t(self):
        # 10^12: EN "T" (trillion short-scale) becomes FR "Bn" (billion
        # long-scale, i.e. 10^12 in French).
        self.assertEqual(millify(3_500_000_000_000, lang="fr"), "3,50 Bn")

    def test_fr_small_number_has_comma_no_suffix(self):
        self.assertEqual(millify(750, lang="fr"), "750,00")


if __name__ == '__main__':
    unittest.main()
