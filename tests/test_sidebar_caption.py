"""The caption under the emblem gives the institution's full chain, as on the
letterhead of the Direction Générale du Budget et des Finances."""
import json
import os
import pathlib
import subprocess
import sys
import unittest

# Imports app and prints the caption lines of the sidebar.
_CAPTION = """
import json
import app

def find(component, class_name):
    if getattr(component, "className", None) == class_name:
        return component
    children = getattr(component, "children", None)
    for child in children if isinstance(children, list) else [children]:
        if hasattr(child, "children"):
            found = find(child, class_name)
            if found is not None:
                return found
    return None

caption = find(app.sidebar, "brand-caption")
print(json.dumps([[line.className, line.children] for line in caption.children]))
"""


class SidebarCaptionTest(unittest.TestCase):

    def test_caption_is_the_letterhead_chain(self):
        result = subprocess.run(
            [sys.executable, "-c", _CAPTION],
            cwd=pathlib.Path(__file__).resolve().parent.parent,
            env=os.environ, capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]), [
            ["brand-country", "République Togolaise"],
            ["brand-institution", "Ministère des Finances et du Budget"],
            ["brand-institution", "Secrétariat Général"],
            ["brand-institution", "Direction Générale du Budget et des Finances"],
        ])


if __name__ == "__main__":
    unittest.main()
