"""
Visualization Theme and Color Utilities

Color palettes based on:
- World Bank Group Brand Guidelines
- World Bank Data Visualization Guidelines (ColorBrewer 2.0 approved schemes)
"""

import os

import plotly.graph_objects as go
import plotly.io as pio

# =============================================================================
# THEME CONSTANTS
# =============================================================================

VALID_THEMES = ["wbg", "quartz"]
_env_theme = os.getenv("DEFAULT_THEME", "").lower()
DEFAULT_THEME = _env_theme if _env_theme in VALID_THEMES else "wbg"

# =============================================================================
# COLOR MANIPULATION UTILITIES
# =============================================================================


def _hex_to_rgb(hex_color):
    """Parse hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def _rgb_to_hex(r, g, b):
    """Convert RGB values to hex color."""
    return f"#{r:02x}{g:02x}{b:02x}"


def darken_color(hex_color, factor=0.7):
    """Darken a hex color by a factor (0-1, lower is darker)."""
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(int(r * factor), int(g * factor), int(b * factor))


def lighten_color(hex_color, factor=0.4):
    """Lighten a hex color by blending with white."""
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return _rgb_to_hex(r, g, b)


def add_opacity(color, opacity):
    """Add opacity to a color. Supports hex (#RRGGBB), rgb(), and rgba() formats."""
    if color.startswith("#"):
        r, g, b = _hex_to_rgb(color)
        return f"rgba({r},{g},{b},{opacity})"
    elif color.startswith("rgb"):
        start = 5 if color.startswith("rgba(") else 4
        parts = color[start:-1].split(",")
        return f"rgba({parts[0].strip()},{parts[1].strip()},{parts[2].strip()},{opacity})"
    else:
        return color


# =============================================================================
# WBG CORPORATE COLORS
# =============================================================================

SOLID_BLUE = "#002244"
BRIGHT_BLUE = "#009FDA"
BLACK = "#000000"
WHITE = "#FFFFFF"

PRIMARY_COLORS = {
    "solid_blue": SOLID_BLUE,
    "bright_blue": BRIGHT_BLUE,
    "black": BLACK,
    "white": WHITE,
}

# =============================================================================
# CENTRAL VS REGIONAL COLORS
# =============================================================================

CENTRAL_COLOR = "rgb(17, 141, 255)"
REGIONAL_COLOR = "rgb(160, 209, 255)"

# =============================================================================
# WBG SECONDARY COLORS
# =============================================================================

WARM_BRIGHTER = ["#F05023", "#FDB714", "#EB1C2D", "#F78D28"]
COOL_BRIGHTER = ["#009CA7", "#00AB51", "#872B90", "#00A996"]
NEUTRAL_WARM = ["#98252B", "#E16A2D", "#B88C1D"]
NEUTRAL_COOL = ["#614776", "#006068", "#006450"]

SECONDARY_COLORS = {
    "warm_brighter": WARM_BRIGHTER,
    "cool_brighter": COOL_BRIGHTER,
    "neutral_warm": NEUTRAL_WARM,
    "neutral_cool": NEUTRAL_COOL,
}

TREEMAP_PALETTE = ["#FDB714", "#F78D28", "#F05023"]  # yellow → amber → orange

# =============================================================================
# DATA VISUALIZATION PALETTES (ColorBrewer 2.0)
# =============================================================================

SEQUENTIAL = [
    "#0c2c84",
    "#225ea8",
    "#1d91c0",
    "#41b6c4",
    "#7fcdbb",
    "#c7e9b4",
    "#edf8b1",
    "#ffffd9",
]

DIVERGING = [
    "#b2182b",
    "#d6604d",
    "#f4a582",
    "#fddbc7",
    "#d1e5f0",
    "#92c5de",
    "#4393c3",
    "#2166ac",
]

QUALITATIVE = [
    "#a6cee3",
    "#1f78b4",
    "#b2df8a",
    "#33a02c",
    "#fb9a99",
    "#e31a1c",
    "#fdbf6f",
    "#ff7f00",
    "#cab2d6",
    "#6a3d9a",
]

QUALITATIVE_ALT = [
    "#8dd3c7",
    "#ffffb3",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
]

VIZ_PALETTES = {
    "sequential": SEQUENTIAL,
    "diverging": DIVERGING,
    "qualitative": QUALITATIVE,
    "qualitative_alt": QUALITATIVE_ALT,
}

# =============================================================================
# PLOTLY COLOR SCALES
# =============================================================================

SEQUENTIAL_SCALE = [
    [0.0, "#0c2c84"],
    [0.14, "#225ea8"],
    [0.28, "#1d91c0"],
    [0.42, "#41b6c4"],
    [0.57, "#7fcdbb"],
    [0.71, "#c7e9b4"],
    [0.85, "#edf8b1"],
    [1.0, "#ffffd9"],
]

DIVERGING_SCALE = [
    [0.0, "#b2182b"],
    [0.14, "#d6604d"],
    [0.28, "#f4a582"],
    [0.42, "#fddbc7"],
    [0.57, "#d1e5f0"],
    [0.71, "#92c5de"],
    [0.85, "#4393c3"],
    [1.0, "#2166ac"],
]

# =============================================================================
# CHART TYPOGRAPHY
# =============================================================================

CHART_FONT_SIZE = 12
CHART_TITLE_FONT_SIZE = 16
CHART_LEGEND_FONT_SIZE = 10

# =============================================================================
# PALETTE HELPERS
# =============================================================================


def get_qualitative_colors(n: int) -> list:
    """Get n colors from the qualitative palette. Cycles if n > len."""
    return [QUALITATIVE[i % len(QUALITATIVE)] for i in range(n)]


def get_sequential_colors(n: int) -> list:
    """Get n evenly spaced colors from the sequential palette."""
    if n <= 1:
        return [SEQUENTIAL[-1]]
    indices = [int(i * (len(SEQUENTIAL) - 1) / (n - 1)) for i in range(n)]
    return [SEQUENTIAL[i] for i in indices]


def get_diverging_colors(n: int) -> list:
    """Get n evenly spaced colors from the diverging palette."""
    if n <= 1:
        return [DIVERGING[len(DIVERGING) // 2]]
    indices = [int(i * (len(DIVERGING) - 1) / (n - 1)) for i in range(n)]
    return [DIVERGING[i] for i in indices]


def create_category_color_map(categories: list, palette: str = "qualitative") -> dict:
    """Create a mapping of categories to colors."""
    palettes = {
        "qualitative": QUALITATIVE,
        "sequential": SEQUENTIAL,
        "diverging": DIVERGING,
    }
    colors = palettes.get(palette, QUALITATIVE)
    return {cat: colors[i % len(colors)] for i, cat in enumerate(categories)}


# =============================================================================
# THEME-AWARE HELPERS
# =============================================================================


def get_map_colorscale(theme: str = None):
    """Get color scale for maps based on theme."""
    theme = theme or DEFAULT_THEME
    return SEQUENTIAL_SCALE if theme == DEFAULT_THEME else "Plasma"


# =============================================================================
# GLOBAL CHART TEMPLATE
# =============================================================================

CHART_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(size=CHART_FONT_SIZE),
        title=dict(font=dict(size=CHART_TITLE_FONT_SIZE)),
        legend=dict(font=dict(size=CHART_LEGEND_FONT_SIZE), borderwidth=0),
        coloraxis=dict(colorbar=dict(outlinewidth=0)),
        xaxis=dict(showgrid=False, zeroline=False, automargin=True),
        yaxis=dict(showgrid=False, zeroline=False, automargin=True),
        colorway=QUALITATIVE,
    )
)


def init_plotly_theme():
    """Register and set the app's Plotly template as the default. Call once at app startup."""
    pio.templates["app"] = CHART_TEMPLATE
    pio.templates.default = "app"
