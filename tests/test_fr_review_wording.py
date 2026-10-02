"""French wording requested in the 28-31 August 2026 review of the Togo dashboard."""
import unittest
from unittest.mock import patch

import pandas as pd

from translations import t

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
            "récurrentes a enregistré le meilleur taux d'exécution, à 105,4 %, tandis que la catégorie "
            "des dépenses d'investissement a accusé le plus fort retard, à 13,4 %.",
        )

    def test_singular_category_takes_de_la(self):
        df = pd.DataFrame({
            "year": [2024, 2024],
            "econ": ["Wage bill", "Capital expenditures"],
            "execution_rate": [99.6, 11.3],
        })

        text = _format_econ_execution_clause(df, "Health", lang="fr")

        self.assertIn("la catégorie de la masse salariale a enregistré le meilleur taux d'exécution", text)


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
        self.assertTrue(t("narrative.health_subnational_context", "fr").startswith(
            "Les disparités régionales dans les dépenses publiques de santé peuvent compromettre la "
            "couverture sanitaire universelle (CSU, ou UHC en anglais) en créant des écarts dans "
            "l'accès aux services et dans la protection financière."))


class RoiNarrativeTest(unittest.TestCase):

    def test_region_phrases_and_csu(self):
        data = pd.DataFrame({
            "country_name": ["Togo"] * 5,
            "adm1_name": ["Plateaux", "Maritime", "Kara", "Centrale", "Savanes"],
            "outcome_index": [50.0, 40.0, 45.0, 44.0, 43.0],
            "per_capita_expenditure": [10.0, 40.0, 20.0, 21.0, 22.0],
        })

        text = _func_subnat_rank_narrative(2024, "Health", data, lang="fr")

        self.assertIn(
            "Parmi les régions, le retour sur investissement (ROI) des dépenses publiques de santé, "
            "mesuré par l'indice CSU (ou UHC), a été le plus élevé pour la région des Plateaux et le "
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

        text = _func_subnat_rank_narrative(2024, "Health", data, lang="fr")

        self.assertIn("le plus élevé pour Nairobi et le plus faible pour Mombasa.", text)

    def test_english_unchanged(self):
        data = pd.DataFrame({
            "country_name": ["Togo"] * 3,
            "adm1_name": ["Plateaux", "Maritime", "Kara"],
            "outcome_index": [50.0, 40.0, 45.0],
            "per_capita_expenditure": [10.0, 40.0, 20.0],
        })

        text = _func_subnat_rank_narrative(2024, "Health", data, lang="en")

        self.assertIn("Plateaux", text)
        self.assertNotIn("région", text)


if __name__ == "__main__":
    unittest.main()
