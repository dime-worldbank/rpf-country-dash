import unittest
from unittest.mock import patch

import pandas as pd

from components.fiscal_balance import narrative


class TestFiscalBalanceNarrativeWEO(unittest.TestCase):

    @patch("components.fiscal_balance._extract_balance_insights")
    def test_weo_mode_uses_actual_tense_when_all_rows_non_forecast(self, mock_extract):
        mock_extract.return_value = {
            "trend": {"start_year": 2020, "end_year": 2022, "slope": 1.0},
            "extrema": {},
        }

        weo_df = pd.DataFrame(
            {
                "year": [2020, 2021, 2022],
                "revenue": [10, 12, 15],
                "expenditure": [12, 13, 14],
                "forecast": [False, False, False],
            }
        )

        text = narrative(None, None, weo_df, "USD", view_mode="weo", lang="en")

        self.assertIn("improved overall", text)
        self.assertNotIn("is expected to improve overall", text)

    @patch("components.fiscal_balance._extract_balance_insights")
    def test_weo_mode_uses_forecast_tense_for_forecast_rows(self, mock_extract):
        mock_extract.return_value = {
            "trend": {"start_year": 2023, "end_year": 2025, "slope": 1.0},
            "extrema": {},
        }

        weo_df = pd.DataFrame(
            {
                "year": [2023, 2024, 2025],
                "revenue": [10, 12, 15],
                "expenditure": [12, 13, 14],
                "forecast": [True, True, True],
            }
        )

        text = narrative(None, None, weo_df, "USD", view_mode="weo", lang="en")

        self.assertIn("is expected to improve overall", text)

    @patch("components.fiscal_balance._extract_balance_insights")
    def test_composite_weo_period_starts_after_gfs_when_no_national(self, mock_extract):
        mock_extract.return_value = {
            "trend": {"start_year": 2021, "end_year": 2022, "slope": 1.0},
            "extrema": {},
        }

        gfs_df = pd.DataFrame(
            {
                "year": [2018, 2019, 2020],
                "revenue": [10, 11, 12],
                "expenditure": [12, 13, 14],
            }
        )
        weo_df = pd.DataFrame(
            {
                "year": [2019, 2020, 2021, 2022],
                "revenue": [10, 11, 12, 13],
                "expenditure": [12, 13, 14, 15],
            }
        )

        narrative(None, gfs_df, weo_df, "USD", view_mode="composite", lang="en")

        self.assertEqual(mock_extract.call_count, 2)
        gfs_call_df = mock_extract.call_args_list[0][0][0]
        weo_call_df = mock_extract.call_args_list[1][0][0]

        self.assertEqual(gfs_call_df["year"].tolist(), [2018, 2019, 2020])
        self.assertEqual(weo_call_df["year"].tolist(), [2021, 2022])

    def test_composite_weo_mixed_actual_and_forecast_uses_mixed_tense(self):
        weo_df = pd.DataFrame(
            {
                "year": [2020, 2021, 2022, 2023],
                "revenue": [100.0, 102.0, 104.0, 106.0],
                "expenditure": [102.0, 103.0, 104.2, 104.5],
                "forecast": [False, False, True, True],
            }
        )

        text = narrative(None, None, weo_df, "USD", view_mode="composite", lang="en")

        self.assertIn("improved overall", text)
        self.assertIn("is expected to improve overall", text)


if __name__ == "__main__":
    unittest.main()
