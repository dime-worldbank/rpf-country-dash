import unittest
from viz_theme import add_opacity, darken_color, lighten_color, _hex_to_rgb, _rgb_to_hex


class TestHexToRgb(unittest.TestCase):
    def test_basic_colors(self):
        self.assertEqual(_hex_to_rgb("#FF0000"), (255, 0, 0))
        self.assertEqual(_hex_to_rgb("#00FF00"), (0, 255, 0))
        self.assertEqual(_hex_to_rgb("#0000FF"), (0, 0, 255))

    def test_without_hash(self):
        self.assertEqual(_hex_to_rgb("FF0000"), (255, 0, 0))

    def test_mixed_case(self):
        self.assertEqual(_hex_to_rgb("#ff0000"), (255, 0, 0))
        self.assertEqual(_hex_to_rgb("#Ff00fF"), (255, 0, 255))


class TestRgbToHex(unittest.TestCase):
    def test_basic_colors(self):
        self.assertEqual(_rgb_to_hex(255, 0, 0), "#ff0000")
        self.assertEqual(_rgb_to_hex(0, 255, 0), "#00ff00")
        self.assertEqual(_rgb_to_hex(0, 0, 255), "#0000ff")

    def test_black_and_white(self):
        self.assertEqual(_rgb_to_hex(0, 0, 0), "#000000")
        self.assertEqual(_rgb_to_hex(255, 255, 255), "#ffffff")


class TestAddOpacity(unittest.TestCase):
    def test_hex_color(self):
        self.assertEqual(add_opacity("#FF0000", 0.5), "rgba(255,0,0,0.5)")
        self.assertEqual(add_opacity("#00FF00", 1), "rgba(0,255,0,1)")

    def test_rgb_color(self):
        self.assertEqual(add_opacity("rgb(255, 0, 0)", 0.5), "rgba(255,0,0,0.5)")
        self.assertEqual(add_opacity("rgb(0,255,0)", 0.8), "rgba(0,255,0,0.8)")

    def test_rgb_with_spaces(self):
        self.assertEqual(add_opacity("rgb( 255 , 128 , 64 )", 0.5), "rgba(255,128,64,0.5)")

    def test_rgba_replaces_alpha(self):
        self.assertEqual(add_opacity("rgba(255, 0, 0, 0.3)", 0.5), "rgba(255,0,0,0.5)")
        self.assertEqual(add_opacity("rgba(0,255,0,1)", 0.2), "rgba(0,255,0,0.2)")

    def test_rgba_with_spaces(self):
        self.assertEqual(add_opacity("rgba( 255 , 128 , 64 , 0.9 )", 0.5), "rgba(255,128,64,0.5)")

    def test_unknown_format_unchanged(self):
        self.assertEqual(add_opacity("hsl(0, 100%, 50%)", 0.5), "hsl(0, 100%, 50%)")
        self.assertEqual(add_opacity("invalid", 0.5), "invalid")


class TestDarkenColor(unittest.TestCase):
    def test_darken_red(self):
        result = darken_color("#FF0000", 0.5)
        self.assertEqual(result, "#7f0000")

    def test_darken_white(self):
        result = darken_color("#FFFFFF", 0.5)
        self.assertEqual(result, "#7f7f7f")

    def test_default_factor(self):
        result = darken_color("#FF0000")
        self.assertEqual(result, "#b20000")


class TestLightenColor(unittest.TestCase):
    def test_lighten_red(self):
        result = lighten_color("#FF0000", 0.5)
        self.assertEqual(result, "#ff7f7f")

    def test_lighten_black(self):
        result = lighten_color("#000000", 0.5)
        self.assertEqual(result, "#7f7f7f")

    def test_default_factor(self):
        result = lighten_color("#FF0000")
        self.assertEqual(result, "#ff6666")


if __name__ == "__main__":
    unittest.main()
