"""
WBG Color Palettes and Constants

Based on:
- World Bank Group Brand Guidelines (https://worldbankgroup.sharepoint.com/sites/wbgsd/Documents/GSDPM/WBG_BrandGuidelines.pdf)
- World Bank Data Visualization Guidelines (https://worldbankgroup.sharepoint.com/sites/office-of-web-standards/SitePages/SystemPages/Detail.aspx/Documents/mode=view?_Id=4)
"""

import plotly.express as px

# =============================================================================
# WBG CORPORATE COLORS (Brand Guidelines p.18)
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
# WBG SECONDARY COLORS (Brand Guidelines p.19)
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

# =============================================================================
# DATA VISUALIZATION PALETTES (Data Visualization Guidelines)
# ColorBrewer 2.0 approved schemes
# =============================================================================

SEQUENTIAL = [
    "#ffffd9",
    "#edf8b1",
    "#c7e9b4",
    "#7fcdbb",
    "#41b6c4",
    "#1d91c0",
    "#225ea8",
    "#0c2c84",
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

VIZ_PALETTES = {
    "sequential": SEQUENTIAL,
    "diverging": DIVERGING,
    "qualitative": QUALITATIVE,
}

# =============================================================================
# PLOTLY COLOR SCALE DEFINITIONS
# For use with continuous color scales in Plotly
# =============================================================================

SEQUENTIAL_SCALE = [
    [0.0, "#ffffd9"],
    [0.14, "#edf8b1"],
    [0.28, "#c7e9b4"],
    [0.42, "#7fcdbb"],
    [0.57, "#41b6c4"],
    [0.71, "#1d91c0"],
    [0.85, "#225ea8"],
    [1.0, "#0c2c84"],
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
# TYPOGRAPHY (for Plotly charts)
# =============================================================================

CHART_FONT_FAMILY = "Open Sans, Arial, sans-serif"
CHART_FONT_SIZE = 12
CHART_LEGEND_FONT_SIZE = 10
CHART_TITLE_FONT_SIZE = 14

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_qualitative_colors(n: int) -> list:
    """
    Get n colors from the qualitative palette.
    Cycles through palette if n > 8.
    """
    return [QUALITATIVE[i % len(QUALITATIVE)] for i in range(n)]


def get_sequential_colors(n: int) -> list:
    """
    Get n evenly spaced colors from the sequential palette.
    """
    if n <= 1:
        return [SEQUENTIAL[-1]]
    indices = [int(i * (len(SEQUENTIAL) - 1) / (n - 1)) for i in range(n)]
    return [SEQUENTIAL[i] for i in indices]


def get_diverging_colors(n: int) -> list:
    """
    Get n evenly spaced colors from the diverging palette.
    """
    if n <= 1:
        return [DIVERGING[len(DIVERGING) // 2]]
    indices = [int(i * (len(DIVERGING) - 1) / (n - 1)) for i in range(n)]
    return [DIVERGING[i] for i in indices]


def create_category_color_map(categories: list, palette: str = "qualitative") -> dict:
    """
    Create a mapping of categories to colors.

    Args:
        categories: List of category names
        palette: One of 'qualitative', 'sequential', 'diverging'

    Returns:
        Dictionary mapping category names to hex colors
    """
    palettes = {
        "qualitative": QUALITATIVE,
        "sequential": SEQUENTIAL,
        "diverging": DIVERGING,
    }
    colors = palettes.get(palette, QUALITATIVE)
    return {cat: colors[i % len(colors)] for i, cat in enumerate(categories)}


def get_chart_layout_defaults() -> dict:
    """
    Get default Plotly layout settings for WBG-compliant charts.
    """
    return {
        "font": {
            "family": CHART_FONT_FAMILY,
            "size": CHART_FONT_SIZE,
            "color": BLACK,
        },
        "title": {
            "font": {
                "family": CHART_FONT_FAMILY,
                "size": CHART_TITLE_FONT_SIZE,
            }
        },
        "legend": {
            "font": {
                "family": CHART_FONT_FAMILY,
                "size": CHART_LEGEND_FONT_SIZE,
            }
        },
        "paper_bgcolor": WHITE,
        "plot_bgcolor": WHITE,
    }


def apply_wbg_style(fig):
    """
    Apply WBG styling to a Plotly figure.

    Args:
        fig: Plotly figure object

    Returns:
        Modified figure with WBG styling applied
    """
    fig.update_layout(**get_chart_layout_defaults())
    return fig


# =============================================================================
# THEME-AWARE HELPERS
# =============================================================================

DEFAULT_QUALITATIVE = px.colors.qualitative.Plotly
DEFAULT_SEQUENTIAL = px.colors.sequential.Viridis
DEFAULT_DIVERGING = px.colors.diverging.RdBu


def get_palette(palette_type: str = "qualitative", theme: str = "wbg") -> list:
    """
    Get color palette based on theme.

    Args:
        palette_type: One of 'qualitative', 'sequential', 'diverging'
        theme: One of 'wbg', 'quartz'

    Returns:
        List of hex color strings
    """
    if theme == "wbg":
        palettes = {
            "qualitative": QUALITATIVE,
            "sequential": SEQUENTIAL,
            "diverging": DIVERGING,
        }
    else:
        palettes = {
            "qualitative": list(DEFAULT_QUALITATIVE),
            "sequential": list(DEFAULT_SEQUENTIAL),
            "diverging": list(DEFAULT_DIVERGING),
        }
    return palettes.get(palette_type, palettes["qualitative"])


def get_color_scale(scale_type: str = "sequential", theme: str = "wbg") -> list:
    """
    Get Plotly color scale based on theme.

    Args:
        scale_type: One of 'sequential', 'diverging'
        theme: One of 'wbg', 'quartz'

    Returns:
        Plotly-compatible color scale
    """
    if theme == "wbg":
        scales = {
            "sequential": SEQUENTIAL_SCALE,
            "diverging": DIVERGING_SCALE,
        }
        return scales.get(scale_type, SEQUENTIAL_SCALE)
    else:
        scales = {
            "sequential": "Viridis",
            "diverging": "RdBu",
        }
        return scales.get(scale_type, "Viridis")


def apply_theme_style(fig, theme: str = "wbg"):
    """
    Apply theme-appropriate styling to a Plotly figure.

    Args:
        fig: Plotly figure object
        theme: One of 'wbg', 'quartz'

    Returns:
        Modified figure with theme styling applied
    """
    if theme == "wbg":
        fig.update_layout(**get_chart_layout_defaults())
    return fig
