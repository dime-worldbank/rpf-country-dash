import pandas as pd
from dash import html
import dash_bootstrap_components as dbc


# ---------------------------------------------------------------------------
# Shared source definitions – define once, reuse across charts.
# Override fields per chart with {**_SOURCE, "label": "Custom Label"}.
# ---------------------------------------------------------------------------

_POVERTY_DESCRIPTION = (
    "Poverty thresholds vary by country income classification: "
    "$3.00 for Low Income, $4.20 for Lower Middle Income, "
    "and $8.30 for Upper Middle and High Income countries."
)

_BOOST = {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"}
_BOOST_EDU = {**_BOOST, "label": "Public Education Expenditure"}
_BOOST_HEALTH = {**_BOOST, "label": "Public Health Expenditure"}

_POVERTY_RATE = {
    "key": "poverty_rate",
    "label": "Poverty Rate",
    "source_name": "World Bank Poverty and Inequality Platform",
    "description": _POVERTY_DESCRIPTION,
}

_SUBNATIONAL_POVERTY = {
    "key": "subnational_poverty_rate",
    "label": "Subnational Poverty Rate",
    "source_name": "World Bank",
    "description": _POVERTY_DESCRIPTION,
}

_LEARNING_POVERTY = {"key": "learning_poverty_rate", "label": "Learning Poverty Rate", "source_name": "World Bank"}

_HD_INDEX = {"key": "global_data_lab_hd_index", "label": "Subnational Human Development Index", "source_name": "Global Data Lab"}

_ATTENDANCE = {"key": "global_data_lab_attendance", "label": "School Attendance Rate", "source_name": "Global Data Lab"}

_UHC = {"key": "universal_health_coverage_index_gho", "label": "Universal Health Coverage Index", "source_name": "WHO (GHO)"}

_PEFA = {
    "key": "pefa_by_pillar",
    "label": "PEFA Assessment",
    "source_name": "PEFA Secretariat",
    "description": (
        "PEFA assessments use letter grades (A to D, with + "
        "modifiers). For this dashboard, grades are converted to "
        "numerical scores (A=4, B+=3.5, B=3, C+=2.5, C=2, D+=1.5, "
        "D=1). Pillar scores are the arithmetic mean of their "
        "constituent indicators. "
        "Data covers both the 2011 framework (28 indicators, 6 "
        "pillars) and the 2016 framework (31 indicators, 7 pillars)."
    ),
}

_EDU_PRIVATE = {
    "key": "edu_private_expenditure",
    "label": "Private Education Expenditure",
    "source_name": "World Bank ICP",
    "source_url": "https://www.worldbank.org/en/programs/icp/data",
    "description": (
        "Derived as total education spending from the International "
        "Comparison Program (ICP) minus BOOST public education "
        "expenditure."
    ),
}

_HEALTH_PRIVATE = {
    "key": "health_private_expenditure",
    "label": "Out-of-Pocket Health Expenditure",
    "source_name": "WHO Global Health Expenditure Database",
    "source_url": "https://apps.who.int/nha/database/",
    "description": (
        "Out-of-pocket spending per person, calculated from "
        "total health expenditure and the share paid out of "
        "pocket, adjusted for inflation."
    ),
}


# ---------------------------------------------------------------------------
# Chart-level metadata for the ⓘ info buttons.
# Keyed by chart ID (matches the ``index`` used in ``source_info_button``).
# Dynamic per-country coverage years and source URLs are merged at runtime.
# ---------------------------------------------------------------------------
CHART_METADATA = {
    # ------------------------------------------------------------------
    # Home – Over Time
    # ------------------------------------------------------------------
    "home-total-exp": {"sources": [_BOOST]},
    "home-percapita-exp": {"sources": [_BOOST, _POVERTY_RATE]},
    "home-func-breakdown": {"sources": [_BOOST]},
    "home-func-growth": {"sources": [_BOOST]},
    "home-econ-breakdown": {"sources": [_BOOST]},
    "home-pefa-overall": {"sources": [_PEFA, _POVERTY_RATE]},
    "home-pefa-pillar": {"sources": [_PEFA]},
    # ------------------------------------------------------------------
    # Home – Across Space
    # ------------------------------------------------------------------
    "home-regional-spending": {"sources": [_BOOST]},
    "home-regional-poverty": {"sources": [_SUBNATIONAL_POVERTY]},
    # ------------------------------------------------------------------
    # Education – Over Time
    # ------------------------------------------------------------------
    "edu-public-private": {"sources": [_BOOST_EDU, _EDU_PRIVATE]},
    "edu-total": {"sources": [_BOOST]},
    "edu-outcome": {"sources": [_BOOST_EDU, _LEARNING_POVERTY, _ATTENDANCE]},
    "edu-opvcap": {"sources": [_BOOST]},
    # ------------------------------------------------------------------
    # Education – Across Space
    # ------------------------------------------------------------------
    "edu-central-regional": {"sources": [_BOOST]},
    "edu-sub-func": {"sources": [_BOOST]},
    "edu-expenditure-map": {"sources": [_BOOST]},
    "edu-outcome-map": {"sources": [_HD_INDEX]},
    "edu-subnational": {"sources": [_BOOST_EDU, _HD_INDEX]},
    # ------------------------------------------------------------------
    # Health – Over Time
    # ------------------------------------------------------------------
    "health-public-private": {"sources": [_BOOST_HEALTH, _HEALTH_PRIVATE]},
    "health-total": {"sources": [_BOOST]},
    "health-outcome": {"sources": [_BOOST_HEALTH, _UHC]},
    "health-opvcap": {"sources": [_BOOST]},
    # ------------------------------------------------------------------
    # Health – Across Space
    # ------------------------------------------------------------------
    "health-central-regional": {"sources": [_BOOST]},
    "health-sub-func": {"sources": [_BOOST]},
    "health-expenditure-map": {"sources": [_BOOST]},
    "health-outcome-map": {"sources": [_UHC]},
    "health-subnational": {"sources": [_BOOST_HEALTH, _UHC]},
}


def source_info_button(index):
    """Renders a small circular ⓘ info icon button.

    Positioned absolutely in the top-right corner of the chart container.
    ``index`` is a chart key that appears in :data:`CHART_METADATA`.
    """
    return dbc.Button(
        "\u24D8",
        id={"type": "source-info-btn", "index": index},
        style={
            "fontSize": "18px",
            "width": "28px",
            "height": "28px",
            "padding": "0",
            "borderRadius": "50%",
            "backgroundColor": "rgba(200, 200, 200, 0.3)",
            "color": "#555555",
            "border": "none",
            "position": "absolute",
            "top": "6px",
            "right": "6px",
            "zIndex": "1000",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
        },
    )


def chart_container(chart_id, graph_component, info_index):
    """Wrap a chart with the Details button overlaid in top-right.

    Args:
        chart_id: HTML id for the container
        graph_component: The dcc.Graph component
        info_index: The chart key for CHART_METADATA lookup
    """
    return html.Div(
        [
            source_info_button(info_index),
            graph_component,
            empty_modal(info_index),
        ],
        style={
            "position": "relative",
            "width": "100%",
            "overflow": "visible",
        },
    )


def _make_detail_row(label, value):
    """Helper to make a label-value row in the modal body."""
    return html.Div(
        [
            html.Span(
                f"{label}: ",
                style={"fontWeight": "bold", "color": "#333"},
            ),
            html.Span(value),
        ],
        style={"marginBottom": "8px"},
    )


def _build_source_section(section, country_name=None):
    """Build the Dash components for a single source section.

    ``section`` is a dict with keys: label, source_name, and optionally
    description, source_url, coverage.
    """
    children = []

    # Section heading
    children.append(
        html.H6(
            section.get("label", ""),
            style={
                "color": "#333",
                "marginTop": "12px",
                "marginBottom": "6px",
                "borderBottom": "1px solid #dee2e6",
                "paddingBottom": "4px",
            },
        )
    )

    # Per-source description (right under the heading)
    desc = section.get("description")
    if desc:
        children.append(_make_detail_row("Methodology", html.Span(desc)))

    # Source URL from pipeline (before source name)
    source_url = section.get("source_url")
    if source_url:
        link = html.A(
            source_url,
            href=source_url,
            target="_blank",
            rel="noopener noreferrer",
            style={"wordBreak": "break-all"},
        )
        children.append(_make_detail_row("More info", link))

    # Source name
    source_name = section.get("source_name")
    if source_name:
        children.append(_make_detail_row("Source", html.Span(source_name)))

    # Coverage years
    coverage = section.get("coverage")
    if coverage:
        label = f"Coverage for {country_name}" if country_name else "Coverage"
        children.append(_make_detail_row(label, html.Span(coverage)))

    return html.Div(children)


def build_modal_children(info):
    """
    Build the ModalBody contents for a chart info modal.

    ``info`` is a dict from :data:`CHART_METADATA` augmented with
    ``source_sections`` by the callback.
    Returns a list containing a single :class:`dbc.ModalBody`.
    """
    source_sections = info.get("source_sections", [])

    body = []

    # Close button
    body.append(
        html.Div(
            html.Button(
                "\u00D7",
                id={"type": "source-info-close", "index": info.get("_index", "")},
                style={
                    "background": "none",
                    "border": "none",
                    "fontSize": "24px",
                    "fontWeight": "bold",
                    "color": "#333",
                    "cursor": "pointer",
                    "lineHeight": "1",
                    "padding": "0",
                },
            ),
            style={"textAlign": "right", "marginBottom": "4px"},
        )
    )

    # Per-source sections
    for section in source_sections:
        body.append(_build_source_section(section, country_name=info.get("country_name")))

    return [dbc.ModalBody(body)]


def empty_modal(index):
    """Placeholder modal to be populated dynamically by the MATCH callback."""
    return dbc.Modal(
        [],
        id={"type": "source-info-modal", "index": index},
        is_open=False,
        centered=True,
        size="lg",
        className="source-info-modal",
    )


# ---------------------------------------------------------------------------
# Coverage-year helpers — extract year ranges from pipeline query results.
# ---------------------------------------------------------------------------

def get_coverage_years(key, country, source_meta, expenditure_data=None):
    """
    Return ``(start_year, end_year)`` for a coverage key and country.

    *key* is either ``"boost"`` (looks up from expenditure data) or an
    indicator_key such as ``"pefa_by_pillar"`` (looks up from
    ``indicator_data_availability``).
    """
    if not country:
        return None, None

    if key == "boost":
        if not source_meta:
            return None, None
        boost_rows = source_meta.get("boost_source_urls", [])
        for row in boost_rows:
            if row.get("country_name") == country:
                start = row.get("boost_earliest_year")
                end = row.get("boost_latest_year")
                if start and end:
                    return int(start), int(end)
                return None, None
        return None, None

    if not source_meta:
        return None, None
    indicator_rows = pd.DataFrame(
        source_meta.get("indicator_availability", [])
    )
    if indicator_rows.empty:
        return None, None
    match = indicator_rows[
        (indicator_rows.country_name == country)
        & (indicator_rows.indicator_key == key)
    ]
    if match.empty:
        return None, None
    row = match.iloc[0]
    start = int(row["start_year"]) if pd.notna(row.get("start_year")) else None
    end = int(row["end_year"]) if pd.notna(row.get("end_year")) else None
    return start, end
