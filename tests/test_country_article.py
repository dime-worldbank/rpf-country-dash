"""Country names take their definite article in French narratives: « pour le Togo »,
« Le Togo a exécuté », « pour l'Albanie »."""
import unittest
from unittest.mock import patch

import pandas as pd

from translations import definite, t

with patch("dash.register_page"):
    from components.budget_funding_execution import format_execution_narrative
    from pages.education import outcome_measure, update_education_subnational_motivation_narrative
    from pages.health import update_health_subnational_motivation_narrative
    from pages.home import economic_narrative, functional_narrative


def country(name, lang):
    return t(f"country.{name}", lang, meta=True)


class DefiniteTest(unittest.TestCase):

    def test_french_article_follows_gender_and_elision(self):
        self.assertEqual(definite("fr", country("Togo", "fr")), "le Togo")
        self.assertEqual(definite("fr", country("Colombia", "fr")), "la Colombie")
        self.assertEqual(definite("fr", country("Albania", "fr")), "l'Albanie")
        self.assertEqual(definite("fr", {"name": "Philippines", "plural": True, "feminine": True}),
                         "les Philippines")

    def test_capitalize_for_sentence_start(self):
        self.assertEqual(definite("fr", country("Togo", "fr"), capitalize=True), "Le Togo")

    def test_english_and_portuguese_names_are_kept(self):
        self.assertEqual(definite("en", country("Togo", "en")), "Togo")
        self.assertEqual(definite("pt", country("Togo", "pt")), "o Togo")


class FrenchNarrativesTest(unittest.TestCase):

    def test_education_outcome_measure(self):
        self.assertTrue(outcome_measure("Togo", "fr").startswith(
            "Pour vérifier si c'est le cas pour le Togo, "))
        self.assertTrue(outcome_measure("Togo", "en").startswith(
            t("narrative.education_outcome_measure", "en", country="Togo")[:40]))

    def test_subnational_motivations(self):
        self.assertTrue(update_education_subnational_motivation_narrative("Togo", 2024, "fr").startswith(
            "Pour examiner cela pour le Togo, "))
        self.assertTrue(update_health_subnational_motivation_narrative("Albania", 2024, "fr").startswith(
            "Pour examiner cela pour l'Albanie, "))

    def test_functional_and_economic_intros(self):
        df = pd.DataFrame({"country_name": ["Togo"] * 4, "year": [2023, 2023, 2024, 2024],
                           "func": ["Health", "Education"] * 2,
                           "econ": ["Wage bill", "Capital expenditures"] * 2,
                           "percentage": [40.0, 60.0, 45.0, 55.0]})
        self.assertTrue(functional_narrative(df, "fr").startswith("Pour le Togo, "))
        self.assertTrue(economic_narrative(df, "fr").startswith("Pour le Togo, "))

    def test_execution_lead(self):
        df = pd.DataFrame({"year": [2021, 2022, 2023], "execution_rate": [80.0, 82.0, 81.0]})
        self.assertTrue(format_execution_narrative(df, "Togo", lang="fr").startswith("Le Togo a exécuté "))
        self.assertTrue(format_execution_narrative(df, "Togo", lang="en").startswith("Togo "))

    def test_templates_and_portuguese_unchanged(self):
        self.assertEqual(t("narrative.no_regional_data", "fr", country=definite("fr", country("Togo", "fr"))),
                         "BOOST ne dispose pas de données sur les dépenses locales/régionales pour le Togo. ")
        self.assertEqual(t("detail.coverage_for", "pt", country=definite("pt", country("Togo", "pt"))),
                         "Cobertura para o Togo")


if __name__ == "__main__":
    unittest.main()
