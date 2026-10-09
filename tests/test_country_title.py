import unittest

from components.country_title import title_text


class TestCountryTitle(unittest.TestCase):

    def test_french_contracts_by_gender_and_initial_vowel(self):
        self.assertEqual(title_text("Togo", "fr"), "Les finances publiques du Togo en chiffres")
        self.assertEqual(title_text("Tunisia", "fr"), "Les finances publiques de la Tunisie en chiffres")
        self.assertEqual(title_text("Albania", "fr"), "Les finances publiques de l'Albanie en chiffres")

    def test_portuguese_contracts_the_stored_article(self):
        self.assertEqual(title_text("Togo", "pt"), "As finanças públicas do Togo em números")
        self.assertEqual(title_text("Albania", "pt"), "As finanças públicas da Albânia em números")

    def test_english_possessive(self):
        self.assertEqual(title_text("Togo", "en"), "Togo's public finances in numbers")

    def test_without_a_country_the_title_is_generic(self):
        self.assertEqual(title_text(None, "fr"), "Les finances publiques en chiffres")
        self.assertEqual(title_text("", "en"), "Public finances in numbers")


if __name__ == "__main__":
    unittest.main()
