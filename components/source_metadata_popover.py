import pandas as pd
from dash import html
import dash_bootstrap_components as dbc

from constants import START_YEAR


# ---------------------------------------------------------------------------
# Shared source definitions – define once, reuse across charts.
# Override fields per chart with {**_SOURCE, "label": "Custom Label"}.
# ---------------------------------------------------------------------------

_POVERTY_DESCRIPTION = (
    "Poverty thresholds vary by country income classification: "
    "$3.00 for Low Income, $4.20 for Lower Middle Income, "
    "and $8.30 for Upper Middle and High Income countries."
)

_SUBNATIONAL_POVERTY_DESCRIPTION = (
    _POVERTY_DESCRIPTION + " Subnational poverty rates come from both Global Subnational Atlas of Poverty (GSAP) and Subnational Poverty and Inequality Database (SPID)"
)

_BOOST = {
    "key": "boost",
    "label": "BOOST Expenditure Data",
    "source_name": "World Bank BOOST",
    "source_url": "https://www.worldbank.org/en/programs/boost-portal/country-data",
}
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
    "description": _SUBNATIONAL_POVERTY_DESCRIPTION,
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
    "overview-total": {"sources": [_BOOST]},
    "overview-per-capita": {"sources": [_BOOST, _POVERTY_RATE]},
    "functional-breakdown": {"sources": [_BOOST]},
    "func-growth": {"sources": [_BOOST]},
    "economic-breakdown": {"sources": [_BOOST]},
    "pefa-overall": {"sources": [_PEFA, _POVERTY_RATE]},
    "pefa-by-pillar": {"sources": [_PEFA]},
    # ------------------------------------------------------------------
    # Home – Across Space
    # ------------------------------------------------------------------
    "subnational-spending": {"sources": [_BOOST]},
    "subnational-poverty": {"sources": [_SUBNATIONAL_POVERTY]},
    # ------------------------------------------------------------------
    # Education – Over Time
    # ------------------------------------------------------------------
    "education-public-private": {"sources": [_BOOST_EDU, _EDU_PRIVATE]},
    "education-total": {"sources": [_BOOST]},
    "education-outcome": {"sources": [_BOOST_EDU, _LEARNING_POVERTY, _ATTENDANCE]},
    "econ-breakdown-func-edu": {"sources": [_BOOST]},
    # ------------------------------------------------------------------
    # Education – Across Space
    # ------------------------------------------------------------------
    "education-central-vs-regional": {"sources": [_BOOST]},
    "education-sub-func": {"sources": [_BOOST]},
    "education-expenditure-map": {"sources": [_BOOST]},
    "education-outcome-map": {"sources": [_HD_INDEX]},
    "education-subnational": {"sources": [_BOOST_EDU, _HD_INDEX]},
    # ------------------------------------------------------------------
    # Health – Over Time
    # ------------------------------------------------------------------
    "health-public-private": {"sources": [_BOOST_HEALTH, _HEALTH_PRIVATE]},
    "health-total": {"sources": [_BOOST]},
    "health-outcome": {"sources": [_BOOST_HEALTH, _UHC]},
    "econ-breakdown-func-health": {"sources": [_BOOST]},
    # ------------------------------------------------------------------
    # Health – Across Space
    # ------------------------------------------------------------------
    "health-central-vs-regional": {"sources": [_BOOST]},
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
        #TODO consider moving this styling to css
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


def chart_container(chart_id):
    """Wrap a chart with the Details button overlaid in top-right.

    Args:
        chart_id: HTML id for the container and chart metadata key
    """
    from dash import dcc

    graph = dcc.Graph(id=chart_id, config={"displayModeBar": False})

    return html.Div(
        [
            source_info_button(chart_id),
            graph,
            empty_modal(chart_id),
        ],
        id=chart_id,
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
                className="detail-label",
            ),
            html.Span(value),
        ],
        className="detail-row",
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
            className="source-section-heading",
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
            className="source-info-link",
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

    return html.Div(children, className="rpf-source-section")


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
                #TODO consider moving this styling to css
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

    return [dbc.ModalBody(body, className="rpf-modal-body")]


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
    Return ``(earliest_year, latest_year)`` for a coverage key and country.

    *key* is either ``"boost"`` (looks up from boost_source_urls) or an
    indicator_key such as ``"pefa_by_pillar"`` (looks up from indicator_availability).
    """
    if not country or not source_meta:
        return None, None

    # Select the appropriate data source
    rows = (
        source_meta.get("boost_source_urls", [])
        if key == "boost"
        else source_meta.get("indicator_availability", [])
    )

    # Find matching row
    for row in rows:
        if row.get("country_name") == country and (
            key == "boost" or row.get("indicator_key") == key
        ):
            start = row.get("earliest_year")
            end = row.get("latest_year")
            # Convert to int, return None if missing
            start = max(int(start), START_YEAR) if start else None
            end = int(end) if end else None
            return start, end

    return None, None


def build_modal_info(chart_id, country, source_meta, expenditure_data=None):
    """
    Build the complete info dict for the modal.

    Fetches chart metadata, builds source sections with coverage years
    and URLs, and returns the complete info structure.

    Args:
        chart_id: Chart key from CHART_METADATA
        country: Selected country name
        source_meta: Dict with "boost_source_urls", "indicator_availability",
                     and "source_urls_by_country" from stored data
        expenditure_data: Optional expenditure data for coverage lookup

    Returns:
        Dict with chart metadata, index, country, and source sections
    """
    chart_meta = CHART_METADATA.get(chart_id, {})

    # Get pre-computed source URL map for this country
    source_url_map = (source_meta or {}).get("source_urls_by_country", {}).get(country, {})

    # Build per-source sections
    source_sections = []
    for src in chart_meta.get("sources", []):
        key = src["key"]
        section = {
            "label": src.get("label", ""),
            "source_name": src.get("source_name", ""),
            "description": src.get("description"),
        }

        # Coverage years
        start, end = get_coverage_years(key, country, source_meta, expenditure_data)
        if start and end:
            section["coverage"] = f"{start}–{end}"

        # Source URL: pipeline first, then fall back to config
        section["source_url"] = source_url_map.get(key) or src.get("source_url")

        source_sections.append(section)

    return {
        **chart_meta,
        "_index": chart_id,
        "country_name": country,
        "source_sections": source_sections,
    }
