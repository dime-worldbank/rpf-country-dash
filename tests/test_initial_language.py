import json
import os
import pathlib
import subprocess
import sys
import unittest

from translations import DEFAULT_LANGUAGE, initial_ui_language, selected_language, t

# Imports app with DEFAULT_LANGUAGE set and prints the text the layout
# renders before any callback runs.
_LAYOUT_TEXTS = """
import json
import app

def find(component, component_id):
    if getattr(component, "id", None) == component_id:
        return component
    children = getattr(component, "children", None)
    for child in children if isinstance(children, list) else [children]:
        if hasattr(child, "children") or hasattr(child, "id"):
            found = find(child, component_id)
            if found is not None:
                return found
    return None

root = app.layout()
print(json.dumps({
    "footer": find(root, "footer-acknowledgment").children,
    "logout": find(root, "logout-tooltip").children,
}))
"""


class InitialUiLanguageTest(unittest.TestCase):

    def test_supported_language_is_used(self):
        self.assertEqual(initial_ui_language("fr"), "fr")
        self.assertEqual(initial_ui_language(" PT "), "pt")

    def test_unset_or_unknown_falls_back_to_default(self):
        for value in (None, "", "de"):
            with self.subTest(value=value):
                self.assertEqual(initial_ui_language(value), DEFAULT_LANGUAGE)


class SelectedLanguageTest(unittest.TestCase):

    def test_click_on_a_language_link_selects_it(self):
        self.assertEqual(selected_language({"type": "lang-link", "index": "fr"}, "en", "en"), "fr")

    def test_page_load_keeps_the_stored_choice(self):
        # Returning the value (not "no change") lets the callbacks that read
        # the language - sidebar links, active link - run on load.
        self.assertEqual(selected_language(None, "pt", "fr"), "pt")

    def test_page_load_without_stored_choice_uses_the_opening_language(self):
        for stored in (None, "", "de"):
            with self.subTest(stored=stored):
                self.assertEqual(selected_language(None, stored, "fr"), "fr")


class OpeningLanguageLayoutTest(unittest.TestCase):

    def test_layout_text_renders_in_the_opening_language(self):
        result = subprocess.run(
            [sys.executable, "-c", _LAYOUT_TEXTS],
            cwd=pathlib.Path(__file__).resolve().parent.parent,
            env={**os.environ, "DEFAULT_LANGUAGE": "fr"},
            capture_output=True, text=True, check=True,
        )
        texts = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(texts["footer"], t("footer.supported_by", "fr"))
        self.assertEqual(texts["logout"], t("nav.logout", "fr"))


if __name__ == "__main__":
    unittest.main()
