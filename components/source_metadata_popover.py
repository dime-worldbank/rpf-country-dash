import pandas as pd
from dash import html
import dash_bootstrap_components as dbc


# ---------------------------------------------------------------------------
# Chart-level metadata for the ⓘ info buttons.
# Keyed by chart ID (matches the ``index`` used in ``source_info_button``).
# Dynamic per-country coverage years and source URLs are merged at runtime.
#
# Fields:
#   title       – modal header / chart name
#   description – optional chart-level explanatory text (methodology, etc.)
#   sources     – list of data sources used by this chart, each with:
#       key         – pipeline key for coverage-year and URL lookup
#                     ("boost" or an indicator_key)
#       label       – display name for this source section
#       source_name – attribution line
#       description – optional per-source explanatory text
# ---------------------------------------------------------------------------
CHART_METADATA = {
    # ------------------------------------------------------------------
    # Home – Over Time
    # ------------------------------------------------------------------
    "home-total-exp": {
        "title": "Total Expenditure",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "home-percapita-exp": {
        "title": "Per Capita Expenditure & Poverty Rate",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
            {"key": "poverty_rate", "label": "Poverty Rate", "source_name": "World Bank Poverty and Inequality Platform"},
        ],
    },
    "home-func-breakdown": {
        "title": "Spending by Functional Categories",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "home-func-growth": {
        "title": "Budget Growth by Functional Categories",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "home-econ-breakdown": {
        "title": "Spending by Economic Categories",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "home-pefa-overall": {
        "title": "Quality of Budget Institutions (Overall)",
        "sources": [
            {
                "key": "pefa_by_pillar",
                "label": "PEFA Assessment",
                "source_name": "PEFA Secretariat",
                "description": (
                    "PEFA assessments use letter grades (A to D, with + "
                    "modifiers). For this dashboard, grades are converted to "
                    "numerical scores (A=4, B+=3.5, B=3, C+=2.5, C=2, D+=1.5, "
                    "D=1). The overall score is the mean of all pillar scores. "
                    "Data covers both the 2011 framework (28 indicators, 6 "
                    "pillars) and the 2016 framework (31 indicators, 7 pillars)."
                ),
            },
        ],
    },
    "home-pefa-pillar": {
        "title": "Quality of Budget Institutions (By Pillar)",
        "sources": [
            {
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
                    "pillars) and the 2016 framework (31 indicators, 7 pillars). "
                    "The 2016 framework introduced Pillar 3 (Asset & Liability "
                    "Management) and reorganised indicator groupings across "
                    "pillars."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------
    # Home – Across Space
    # ------------------------------------------------------------------
    "home-regional-spending": {
        "title": "Regional Expenditure",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "home-regional-poverty": {
        "title": "Poverty by Region",
        "sources": [
            {"key": "subnational_poverty_rate", "label": "Subnational Poverty Rate", "source_name": "World Bank"},
        ],
    },
    # ------------------------------------------------------------------
    # Education – Over Time
    # ------------------------------------------------------------------
    "edu-public-private": {
        "title": "Who Pays for Education?",
        "sources": [
            {"key": "boost", "label": "Public Education Expenditure", "source_name": "World Bank BOOST"},
            {
                "key": "edu_private_expenditure",
                "label": "Private Education Expenditure",
                "source_name": "World Bank ICP",
                "description": (
                    "Derived as total education spending from the International "
                    "Comparison Program (ICP) minus BOOST public education "
                    "expenditure."
                ),
            },
        ],
    },
    "edu-total": {
        "title": "Total Education Expenditure",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "edu-outcome": {
        "title": "Public Spending & Education Outcome",
        "sources": [
            {"key": "boost", "label": "Public Education Expenditure", "source_name": "World Bank BOOST"},
            {"key": "learning_poverty_rate", "label": "Learning Poverty Rate", "source_name": "World Bank"},
        ],
    },
    "edu-opvcap": {
        "title": "Operational vs. Capital Spending",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    # ------------------------------------------------------------------
    # Education – Across Space
    # ------------------------------------------------------------------
    "edu-central-regional": {
        "title": "Centrally vs. Geographically Allocated Education Spending",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "edu-sub-func": {
        "title": "Education by Sub-functional Categories",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "edu-expenditure-map": {
        "title": "Education Expenditure Map",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "edu-outcome-map": {
        "title": "Education Outcomes Map",
        "sources": [
            {"key": "global_data_lab_hd_index", "label": "Subnational Human Development Index", "source_name": "Global Data Lab"},
        ],
    },
    "edu-subnational": {
        "title": "Public Spending vs. Education Outcomes Across Regions",
        "sources": [
            {"key": "boost", "label": "Public Education Expenditure", "source_name": "World Bank BOOST"},
            {"key": "global_data_lab_hd_index", "label": "Subnational Human Development Index", "source_name": "Global Data Lab"},
        ],
    },
    # ------------------------------------------------------------------
    # Health – Over Time
    # ------------------------------------------------------------------
    "health-public-private": {
        "title": "Who Pays for Healthcare?",
        "sources": [
            {"key": "boost", "label": "Public Health Expenditure", "source_name": "World Bank BOOST"},
            {
                "key": "health_private_expenditure",
                "label": "Out-of-Pocket Health Expenditure",
                "source_name": "WHO Global Health Expenditure Database",
                "description": (
                    "Computed as CHE (current health expenditure in local "
                    "currency) multiplied by OOP % of CHE, then adjusted for "
                    "inflation using CPI. Source indicators: "
                    "GHED_CHEGDP_SHA2011, GHED_OOPSCHE_SHA2011."
                ),
            },
        ],
    },
    "health-total": {
        "title": "Total Health Expenditure",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "health-outcome": {
        "title": "Public Spending & Health Outcome",
        "sources": [
            {"key": "boost", "label": "Public Health Expenditure", "source_name": "World Bank BOOST"},
            {"key": "universal_health_coverage_index_gho", "label": "Universal Health Coverage Index", "source_name": "WHO (GHO)"},
        ],
    },
    "health-opvcap": {
        "title": "Operational vs. Capital Spending",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    # ------------------------------------------------------------------
    # Health – Across Space
    # ------------------------------------------------------------------
    "health-central-regional": {
        "title": "Centrally vs. Geographically Allocated Health Spending",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "health-sub-func": {
        "title": "Health by Sub-functional Categories",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "health-expenditure-map": {
        "title": "Health Expenditure Map",
        "sources": [
            {"key": "boost", "label": "BOOST Expenditure Data", "source_name": "World Bank BOOST"},
        ],
    },
    "health-outcome-map": {
        "title": "Health Outcomes Map",
        "sources": [
            {"key": "universal_health_coverage_index_gho", "label": "Universal Health Coverage Index", "source_name": "WHO (GHO)"},
        ],
    },
    "health-subnational": {
        "title": "Public Spending vs. Health Outcomes Across Regions",
        "sources": [
            {"key": "boost", "label": "Public Health Expenditure", "source_name": "World Bank BOOST"},
            {"key": "universal_health_coverage_index_gho", "label": "Universal Health Coverage Index", "source_name": "WHO (GHO)"},
        ],
    },
}


def source_info_button(index):
    """Renders a small circular info button with an (i) icon.

    ``index`` is a chart key that appears in :data:`CHART_METADATA`.
    The component id is a dict so that a single Dash pattern-matching
    callback can service every button.
    """
    return html.Span(
        dbc.Button(
            [
                html.Span(
                    "\u24D8",
                    style={
                        "fontSize": "16px",
                        "marginRight": "4px",
                        "verticalAlign": "middle",
                    },
                ),
                html.Span(
                    "Details",
                    style={
                        "fontSize": "13px",
                        "verticalAlign": "middle",
                    },
                ),
            ],
            id={"type": "source-info-btn", "index": index},
            size="sm",
            style={
                "padding": "2px 10px",
                "borderRadius": "16px",
                "verticalAlign": "middle",
                "textDecoration": "none",
                "lineHeight": "1.5",
                "backgroundColor": "rgba(255, 255, 255, 0.15)",
                "color": "#ffffff",
                "border": "1px solid rgba(255, 255, 255, 0.5)",
            },
        ),
        style={"marginLeft": "6px"},
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


def _build_source_section(section):
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
        children.append(_make_detail_row("Coverage", html.Span(coverage)))

    return html.Div(children)


def build_modal_children(info):
    """
    Build [ModalHeader, ModalBody] for a chart info modal.

    ``info`` is a dict from :data:`CHART_METADATA` augmented with
    ``source_sections`` by the callback.
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
        body.append(_build_source_section(section))

    return [dbc.ModalBody(body)]


def empty_modal(index):
    """Placeholder modal to be populated dynamically by the MATCH callback."""
    return dbc.Modal(
        [],
        id={"type": "source-info-modal", "index": index},
        is_open=False,
        centered=True,
        size="lg",
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
        if not expenditure_data:
            return None, None
        exp_df = pd.DataFrame(
            expenditure_data.get("expenditure_w_poverty_by_country_year", [])
        )
        if exp_df.empty:
            return None, None
        country_df = exp_df[exp_df.country_name == country]
        if country_df.empty:
            return None, None
        return int(country_df.year.min()), int(country_df.year.max())

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
