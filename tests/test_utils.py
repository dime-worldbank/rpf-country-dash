import unittest
import pandas as pd
import plotly.graph_objects as go
from pandas.testing import assert_frame_equal
import math
from utils import (
    filter_country_sort_year,
    get_correlation_text,
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

    def test_positive_strong_correlation(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("very strong positive", result)

    def test_negative_moderate_correlation(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [-1, -2, -3]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("very strong inverse", result)

    def test_weak_correlation(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 2, 1.5, 3.5, 1]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertRegex(result, r"weak positive")

    def test_no_correlation(self):
        df = pd.DataFrame({"x": [1, 1, 1], "y": [2, 3, 4]})  # constant x
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("unknown due to limited data", result)

    def test_no_association(self):
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [5, 5, 5, 5, 5]})  # constant y
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("unknown due to limited data", result)

    def test_not_enough_data_points(self):
        df = pd.DataFrame({"x": [1, 2], "y": [2, 4]})
        result = get_correlation_text(df, self.x_col, self.y_col)
        self.assertIn("unknown due to limited data", result)
        
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

class TestFormatCurrency(unittest.TestCase):

    def test_thousands(self):
        # Bhutan: 1,000 BTN (Ngultrum) should format as "BTN 1.00 K"
        result = format_currency(1000, "BTN")
        self.assertEqual(result, "BTN 1.00 K")

    def test_millions(self):
        # Kenya: 1.5M KES (Shilling) — typical government budget figure
        result = format_currency(1_500_000, "KES")
        self.assertEqual(result, "KES 1.50 M")

    def test_billions(self):
        # Kenya: 2B KES — national GDP scale
        result = format_currency(2_000_000_000, "KES")
        self.assertEqual(result, "KES 2.00 B")

    def test_small_value(self):
        # Bhutan: 250 BTN — values under 1000 have no suffix
        result = format_currency(250, "BTN")
        self.assertEqual(result, "BTN 250.00")

    def test_zero(self):
        # Zero value edge case with Kenyan Shilling
        result = format_currency(0, "KES")
        self.assertEqual(result, "KES 0.00")

    def test_currency_code_used(self):
        # Ensure the BTN prefix appears in the output
        result = format_currency(5000, "BTN")
        self.assertTrue(result.startswith("BTN "))



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
        self.assertEqual(self.df["expenditure_formatted"].iloc[0], "BTN 1.00 K")
        self.assertEqual(self.df["expenditure_formatted"].iloc[1], "BTN 500.00 K")
        self.assertEqual(self.df["expenditure_formatted"].iloc[2], "BTN 2.00 B")

    def test_formatted_values_correct_kes(self):
        add_currency_column(self.df, "expenditure", "KES")
        self.assertEqual(self.df["expenditure_formatted"].iloc[0], "KES 1.00 K")
        self.assertEqual(self.df["expenditure_formatted"].iloc[1], "KES 500.00 K")
        self.assertEqual(self.df["expenditure_formatted"].iloc[2], "KES 2.00 B")

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


if __name__ == '__main__':
    unittest.main()
