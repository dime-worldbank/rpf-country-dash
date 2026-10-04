import re
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from translations import genitive, t
from utils import get_percentage_change_text

# Page modules call dash.register_page at import, which needs a live app.
with patch("dash.register_page"):
    from pages.education import education_narrative
    from pages.health import health_narrative


def _spending(decentralized, central=None, expenditure=None):
    years = list(range(2019, 2019 + len(decentralized)))
    n = len(years)
    return pd.DataFrame({
        "country_name": ["Togo"] * n,
        "year": years,
        "expenditure": expenditure if expenditure is not None else [100.0 + 10 * i for i in range(n)],
        "real_expenditure": [90.0 + 5 * i for i in range(n)],
        "central_expenditure": central if central is not None else [80.0 + 5 * i for i in range(n)],
        "decentralized_expenditure": decentralized,
        "expenditure_decentralization": [np.nan] * n,
    })


def _before_change_text(key, lang):
    """The part of a spending-change sentence before its change text."""
    return t(key, lang, change_text="\0").split("\0")[0].strip()


def _narratives(spending, lang):
    with patch("pages.education.server_store.get", return_value=spending.copy()), \
         patch("pages.health.server_store.get", return_value=spending.copy()):
        return {
            "education": education_narrative(None, "Togo", lang=lang),
            "health": health_narrative(None, "Togo", lang=lang),
        }


class SubnationalSpendingChangeTest(unittest.TestCase):

    def test_missing_end_year_value_reads_as_unavailable_not_nan(self):
        spending = _spending([20.0, 22.0, np.nan])

        for lang in ("en", "fr", "pt"):
            for page, text in _narratives(spending, lang).items():
                with self.subTest(page=page, lang=lang):
                    self.assertIsNone(re.search(r"\bnan\b", text, re.IGNORECASE), text)
                    self.assertIn(t("narrative.subnational_unavailable", lang).strip(" ."), text)
                    self.assertNotIn(" .", text)

    def test_complete_series_still_reports_the_change(self):
        spending = _spending([20.0, 22.0, 24.0])
        # Inflation-adjusted subnational spending: 90/100 * 20 = 18 in 2019,
        # 100/120 * 24 = 20 in 2021.
        expected = t("narrative.subnational_spending_change", "en",
                     change_text=get_percentage_change_text(20 / 18 - 1, lang="en"))

        for page, text in _narratives(spending, "en").items():
            with self.subTest(page=page):
                self.assertIn(expected.strip(), text)
                self.assertNotIn(t("narrative.subnational_unavailable", "en").strip(" ."), text)
                self.assertIsNone(re.search(r"\bnan\b", text, re.IGNORECASE), text)


class CentralSpendingChangeTest(unittest.TestCase):

    def test_no_year_with_central_spending_gives_the_trend_only(self):
        spending = _spending([20.0, 22.0, 24.0], central=[np.nan, np.nan, np.nan])

        for page, text in _narratives(spending, "en").items():
            with self.subTest(page=page):
                self.assertIn("After accounting for inflation", text)
                self.assertNotIn("central government", text)
                self.assertIsNone(re.search(r"\b(nan|inf)\b", text, re.IGNORECASE), text)

    def test_unusable_central_start_leaves_out_the_spending_comparison(self):
        cases = {
            "zero central start": _spending([20.0, 22.0, 24.0], central=[0.0, 85.0, 90.0]),
            "infinite central start": _spending([20.0, 22.0, 24.0], central=[np.inf, 85.0, 90.0]),
            "zero total in the first year": _spending([20.0, 22.0, 24.0],
                                                      expenditure=[0.0, 110.0, 120.0]),
        }
        for case, spending in cases.items():
            for lang in ("en", "fr", "pt"):
                for page, text in _narratives(spending, lang).items():
                    with self.subTest(case=case, page=page, lang=lang):
                        self._assert_comparison_left_out(text, page, lang)

    def _assert_comparison_left_out(self, text, page, lang):
        self.assertIsNone(re.search(r"\b(nan|inf)\b", text, re.IGNORECASE), text)
        self.assertNotIn(_before_change_text("narrative.central_spending_change", lang), text)
        self.assertNotIn(_before_change_text("narrative.subnational_spending_change", lang), text)
        sector = f"sector.{page}"
        self.assertIn(t("narrative.decentralization_unknown", lang, sector=t(sector, lang),
                        sector_gen=genitive(lang, t(sector, lang, meta=True))), text)
        self.assertNotIn(" .", text)

    def test_single_year_reads_as_unchanged(self):
        spending = _spending([20.0])

        for page, text in _narratives(spending, "en").items():
            with self.subTest(page=page):
                self.assertIsNone(re.search(r"\b(nan|inf)\b", text, re.IGNORECASE), text)
                self.assertIn(t("narrative.central_spending_change", "en",
                                change_text=t("narrative.mostly_unchanged", "en")).strip(), text)

    def test_both_pages_share_one_narrative(self):
        spending = _spending([20.0, 22.0, 24.0])
        texts = _narratives(spending, "en")

        self.assertEqual(texts["education"].replace("education", "SECTOR"),
                         texts["health"].replace("health", "SECTOR"))


if __name__ == "__main__":
    unittest.main()
