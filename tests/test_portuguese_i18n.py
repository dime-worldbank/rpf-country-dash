import unittest
from unittest.mock import patch

import plotly.graph_objects as go

from components.source_metadata_popover import build_modal_info
from translations import (
    _LANGUAGES,
    elide_que,
    genitive,
    get_available_languages,
    localize_currency_name,
    preposition,
    strip_article,
    t,
)
from translations.en import TRANSLATIONS as EN
from translations.pt import TRANSLATIONS as PT
from trend_narrative_i18n import (
    get_relationship_narrative_i18n,
    get_segment_narrative_i18n,
)
from utils import apply_locale, millify


class TestPortugueseTranslations(unittest.TestCase):
    def test_portuguese_registered(self):
        self.assertIn("pt", get_available_languages())

    def test_portuguese_has_same_keys_as_english(self):
        self.assertEqual(set(PT.keys()), set(EN.keys()))

    def test_portuguese_lookup_and_decimal_interpolation(self):
        self.assertEqual(t("nav.health", "pt"), "Saúde")
        self.assertIn("12,3%", t("narrative.decentral_mean", "pt", mean=12.3))

    def test_portuguese_grammar_helpers(self):
        self.assertEqual(preposition("pt", _LANGUAGES["pt"]["sector.health"]), "na saúde")
        self.assertEqual(preposition("pt", _LANGUAGES["pt"]["country.Kenya"]), "no Quênia")
        self.assertEqual(genitive("pt", t("country.Kenya", "pt")), "do Quênia")
        self.assertEqual(strip_article("pt", t("country.Kenya", "pt")), "Quênia")

    def test_elide_que_language_outputs(self):
        self.assertEqual(elide_que("fr", "Afar"), "qu'")
        self.assertEqual(elide_que("fr", "Kampala"), "que ")
        self.assertEqual(elide_que("pt", "Afar"), "que ")
        self.assertEqual(elide_que("en", "Afar"), "that ")
        self.assertEqual(elide_que("es", "Afar"), "that ")

    def test_portuguese_millify_and_plotly_separators(self):
        self.assertEqual(millify(1_500_000, lang="pt"), "1,50 M")
        self.assertEqual(millify(2_000_000_000, lang="pt"), "2,00 bi")

        fig = apply_locale(go.Figure(), lang="pt")
        self.assertEqual(fig.layout.separators, ",.")

    def test_portuguese_currency_name_localization(self):
        self.assertEqual(
            localize_currency_name("Albanian Lek", "pt", currency_code="ALL"),
            "Leks albaneses",
        )
        self.assertEqual(
            localize_currency_name("Kenyan Shilling", "pt", currency_code="KES"),
            "Xelins quenianos",
        )


class TestPortugueseSourceMetadata(unittest.TestCase):
    def setUp(self):
        self.source_meta = {
            "source_registry": [
                {"source_id": "boost", "name": "BOOST", "publisher": "World Bank",
                 "url": "https://www.worldbank.org/en/programs/boost-portal/country-data"},
                {"source_id": "world_bank_pip", "name": "Poverty and Inequality Platform",
                 "publisher": "World Bank", "url": "https://pip.worldbank.org"},
            ],
            "boost_source_urls": [
                {
                    "country_name": "Kenya",
                    "source_url": "https://boost.worldbank.org/kenya",
                    "earliest_year": 2010,
                    "latest_year": 2020,
                }
            ],
            "indicator_availability": [
                {
                    "country_name": "Kenya",
                    "indicator_key": "poverty_rate",
                    "years": [2012, 2015, 2019],
                }
            ],
            # Bridge: overview-per-capita's indicators (boost, poverty_rate) → source_id(s).
            "indicator_source": [
                {"indicator_key": "boost", "source_id": "boost"},
                {"indicator_key": "poverty_rate", "source_id": "world_bank_pip"},
            ],
        }

    def test_build_modal_info_portuguese(self):
        info = build_modal_info("overview-per-capita", "Kenya", self.source_meta, lang="pt")

        boost_section = info["source_sections"][0]
        self.assertEqual(boost_section["label"], "Dados de despesa BOOST")
        # Source line is localized "publisher — name".
        self.assertEqual(boost_section["source_name"], "Banco Mundial — BOOST")

        poverty_section = info["source_sections"][1]
        self.assertEqual(poverty_section["label"], "Taxa de pobreza")
        self.assertIn("Banco Mundial", poverty_section["source_name"])
        self.assertIn("linhas de pobreza", poverty_section["description"])


class TestTrendNarrativeLanguageFallback(unittest.TestCase):
    def test_segment_narrative_falls_back_to_english_for_unsupported_language(self):
        calls = []

        def fake_segment(**kwargs):
            calls.append(kwargs["lang"])
            if kwargs["lang"] == "fr":
                raise ValueError("Unsupported language 'fr'.")
            self.assertEqual(kwargs["metric"], "depense reelle")
            return "English fallback"

        with patch("trend_narrative_i18n.get_segment_narrative", side_effect=fake_segment):
            result = get_segment_narrative_i18n(
                extractor=object(),
                metric="depense reelle",
                lang="fr",
            )

        self.assertEqual(result, "English fallback")
        self.assertEqual(calls, ["fr", "en"])

    def test_relationship_narrative_reraises_non_language_errors(self):
        calls = []

        def fake_relationship(**kwargs):
            calls.append(kwargs["lang"])
            raise RuntimeError("Trend narrative failed")

        with patch("trend_narrative_i18n.get_relationship_narrative", side_effect=fake_relationship):
            with self.assertRaises(RuntimeError):
                get_relationship_narrative_i18n(
                    reference_years=[2020],
                    reference_values=[1],
                    comparison_years=[2020],
                    comparison_values=[2],
                    reference_name="despesa",
                    comparison_name="resultado",
                    lang="pt",
                )

        self.assertEqual(calls, ["pt"])


if __name__ == "__main__":
    unittest.main()
