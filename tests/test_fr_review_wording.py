"""French narrative and heading wording, and the region and sector phrases
the narratives interpolate."""
import unittest
from unittest.mock import patch

import pandas as pd

from translations import _LANGUAGES, t

with patch("dash.register_page"):
    from components.budget_funding_execution import _format_econ_execution_clause
    from components.edu_health_across_space import _func_subnat_rank_narrative


class ExecutionClauseTest(unittest.TestCase):

    def test_category_genitive_and_execution_wording(self):
        df = pd.DataFrame({
            "year": [2024] * 4,
            "econ": ["Other recurrent", "Capital expenditures", "Wage bill", "Goods and services"],
            "execution_rate": [105.4, 13.4, 90.0, 80.0],
        })

        text = _format_econ_execution_clause(df, "Education", lang="fr")

        self.assertEqual(
            text,
            "Au sein du budget de l'éducation, sur la même période, la catégorie des autres dépenses "
            "récurrentes a enregistré, en moyenne, le meilleur taux d'exécution, à 105,4 %, tandis que "
            "la catégorie des dépenses d'investissement a accusé, en moyenne, le plus fort retard, "
            "à 13,4 %.",
        )

    def test_singular_category_takes_de_la(self):
        df = pd.DataFrame({
            "year": [2024, 2024],
            "econ": ["Wage bill", "Capital expenditures"],
            "execution_rate": [99.6, 11.3],
        })

        text = _format_econ_execution_clause(df, "Health", lang="fr")

        self.assertIn("la catégorie de la masse salariale a enregistré, en moyenne, le meilleur taux", text)


class FixedStringsTest(unittest.TestCase):

    def test_subnational_and_decentralization_sentences(self):
        self.assertEqual(
            t("narrative.subnational_unavailable", "fr").strip(" ."),
            "Les données des collectivités territoriales ne sont pas disponibles pour cette période",
        )
        self.assertEqual(
            t("narrative.decentralization_unknown", "fr", sector_gen="de la santé", sector="santé"),
            "Le degré de décentralisation des dépenses de la santé est inconnu en raison de l'absence "
            "de données sur les dépenses publiques locales.",
        )

    def test_subnational_change_uses_the_same_term(self):
        self.assertIn("des collectivités territoriales",
                      t("narrative.subnational_spending_change", "fr", change_text="ont augmenté de 5 %"))

    def test_headings(self):
        self.assertEqual(t("heading.central_vs_geo_education", "fr"),
                         "Dépenses d'éducation : niveau central c. répartition géographique")
        self.assertEqual(t("heading.central_vs_geo_health", "fr"),
                         "Dépenses de santé : niveau central c. répartition géographique")
        self.assertEqual(t("heading.public_spending_health_regions", "fr"),
                         "Dépenses publiques c. résultats sanitaires par région")
        self.assertEqual(t("heading.public_spending_education_regions", "fr"),
                         "Dépenses publiques c. résultats éducatifs par région")

    def test_uhc_context_names_csu(self):
        context = t("narrative.health_subnational_context", "fr")
        self.assertIn(
            "Les disparités régionales dans les dépenses publiques de santé peuvent compromettre la "
            "couverture sanitaire universelle (CSU, ou UHC en anglais) en créant des écarts dans "
            "l'accès aux services et dans la protection financière.", context)
        self.assertNotIn("UHC)", context.replace("(CSU, ou UHC en anglais)", ""))
        self.assertNotIn("la UHC", context)

    def test_csu_on_the_rest_of_the_health_page(self):
        self.assertIn("utilisons l'indice CSU comme indicateur",
                      t("narrative.health_subnational_motivation", "fr", country="Togo", year=2024))
        self.assertEqual(t("outcome.uhc_index", "fr"), "Indice CSU")
        self.assertEqual(t("outcome.uhc_index.narrative", "fr"), "l'indice CSU")
        self.assertIn("CSU", t("source.health_outcome", "fr"))
        self.assertNotIn("UHC", t("source.health_outcome", "fr"))


class RoiNarrativeTest(unittest.TestCase):

    def test_region_phrases_and_csu(self):
        data = pd.DataFrame({
            "country_name": ["Togo"] * 5,
            "adm1_name": ["Plateaux", "Maritime", "Kara", "Centrale", "Savanes"],
            "outcome_index": [50.0, 40.0, 45.0, 44.0, 43.0],
            "per_capita_expenditure": [10.0, 40.0, 20.0, 21.0, 22.0],
        })

        text = _func_subnat_rank_narrative(2024, "Health", data, "Togo", lang="fr")

        self.assertIn(
            "Parmi les régions, le retour sur investissement (ROI) des dépenses publiques de santé, "
            "mesuré par l'indice CSU, a été le plus élevé pour la région des Plateaux et le "
            "plus faible pour la région Maritime.",
            text,
        )

    def test_region_without_phrase_keeps_its_name(self):
        data = pd.DataFrame({
            "country_name": ["Kenya"] * 3,
            "adm1_name": ["Nairobi", "Mombasa", "Kisumu"],
            "outcome_index": [50.0, 40.0, 45.0],
            "per_capita_expenditure": [10.0, 40.0, 20.0],
        })

        text = _func_subnat_rank_narrative(2024, "Health", data, "Kenya", lang="fr")

        self.assertIn("le plus élevé pour Nairobi et le plus faible pour Mombasa.", text)

    def test_region_phrase_never_comes_from_another_language(self):
        data = pd.DataFrame({
            "country_name": ["Kenya"] * 3,
            "adm1_name": ["Nairobi", "Mombasa", "Kisumu"],
            "outcome_index": [50.0, 40.0, 45.0],
            "per_capita_expenditure": [10.0, 40.0, 20.0],
        })

        with patch.dict(_LANGUAGES["en"], {"region.Kenya.Nairobi": "Nairobi County"}):
            text = _func_subnat_rank_narrative(2024, "Health", data, "Kenya", lang="fr")

        self.assertIn("le plus élevé pour Nairobi et", text)

    def test_vowel_sector_elides_de(self):
        data = pd.DataFrame({
            "country_name": ["Togo"] * 3,
            "adm1_name": ["Kara", "Maritime", "Savanes"],
            "outcome_index": [50.0, 40.0, 45.0],
            "per_capita_expenditure": [10.0, 40.0, 20.0],
        })

        text = _func_subnat_rank_narrative(2024, "Education", data, "Togo", lang="fr")

        self.assertIn("des dépenses publiques d'éducation,", text)
        self.assertIn("pour la région de la Kara", text)

    def test_portuguese_keeps_bare_region_names(self):
        data = pd.DataFrame({
            "country_name": ["Togo"] * 3,
            "adm1_name": ["Plateaux", "Maritime", "Kara"],
            "outcome_index": [50.0, 40.0, 45.0],
            "per_capita_expenditure": [10.0, 40.0, 20.0],
        })

        text = _func_subnat_rank_narrative(2024, "Health", data, "Togo", lang="pt")

        self.assertIn("Plateaux teve o maior retorno sobre investimento (ROI), enquanto Maritime teve o menor.",
                      text)

    def test_english_unchanged(self):
        data = pd.DataFrame({
            "country_name": ["Togo"] * 3,
            "adm1_name": ["Plateaux", "Maritime", "Kara"],
            "outcome_index": [50.0, 40.0, 45.0],
            "per_capita_expenditure": [10.0, 40.0, 20.0],
        })

        text = _func_subnat_rank_narrative(2024, "Health", data, "Togo", lang="en")

        self.assertIn(
            "Among the subnational regions, in terms of return on public spending in health measured "
            "by the UHC Index, Plateaux had the highest return on investment (ROI) while Maritime had "
            "the lowest.", text)

if __name__ == "__main__":
    unittest.main()
