import pandas as pd
from dash import html
import dash_bootstrap_components as dbc


# ---------------------------------------------------------------------------
# Chart-level metadata for the ⓘ info buttons.
# Keyed by chart ID (matches the ``index`` used in ``source_info_button``).
# Static descriptive fields live here; dynamic per-country coverage years
# are merged in at runtime from pipeline queries.
#
# Fields:
#   title         – modal header / chart name
#   description   – optional explanatory text (methodology, derivation, etc.)
#   source_name   – attribution line
#   framework_url – optional link to methodology/framework documentation
#   coverage_keys – list of pipeline keys used to look up year ranges
#                   ("boost" for BOOST expenditure, or an indicator_key
#                   from indicator_data_availability)
# ---------------------------------------------------------------------------
CHART_METADATA = {
    # ------------------------------------------------------------------
    # Home – Over Time
    # ------------------------------------------------------------------
    "home-total-exp": {
        "title": "Total Expenditure",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "home-percapita-exp": {
        "title": "Per Capita Expenditure",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "home-func-breakdown": {
        "title": "Spending by Functional Categories",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "home-func-growth": {
        "title": "Budget Growth by Functional Categories",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "home-econ-breakdown": {
        "title": "Spending by Economic Categories",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "home-pefa-overall": {
        "title": "Quality of Budget Institutions (Overall)",
        "source_name": "PEFA Secretariat",

        "framework_url": "https://www.pefa.org/resources/pefa-2016-framework",
        "description": (
            "PEFA assessments use letter grades (A to D, with + "
            "modifiers). For this dashboard, grades are converted to "
            "numerical scores (A=4, B+=3.5, B=3, C+=2.5, C=2, D+=1.5, "
            "D=1). The overall score is the mean of all pillar scores. "
            "Data covers both the 2011 framework (28 indicators, 6 "
            "pillars) and the 2016 framework (31 indicators, 7 pillars)."
        ),
        "coverage_keys": ["pefa_by_pillar", "subnational_poverty_rate"],
    },
    "home-pefa-pillar": {
        "title": "Quality of Budget Institutions (By Pillar)",
        "source_name": "PEFA Secretariat",

        "framework_url": "https://www.pefa.org/resources/pefa-2016-framework",
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
        "coverage_keys": ["pefa_by_pillar"],
    },
    # ------------------------------------------------------------------
    # Home – Across Space
    # ------------------------------------------------------------------
    "home-regional-spending": {
        "title": "Regional Expenditure",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "home-regional-poverty": {
        "title": "Poverty by Region",
        "source_name": "World Bank",

        "coverage_keys": ["subnational_poverty_rate"],
    },
    # ------------------------------------------------------------------
    # Education – Over Time
    # ------------------------------------------------------------------
    "edu-public-private": {
        "title": "Who Pays for Education?",
        "source_name": "World Bank BOOST / ICP",
        "description": (
            "Public expenditure from BOOST. Private expenditure derived "
            "as total education spending from the International "
            "Comparison Program (ICP) minus BOOST public education "
            "expenditure."
        ),
        "coverage_keys": ["boost", "edu_private_expenditure"],
    },
    "edu-total": {
        "title": "Total Education Expenditure",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "edu-outcome": {
        "title": "Public Spending & Education Outcome",
        "source_name": "World Bank BOOST / World Bank",

        "description": (
            "Public education expenditure from BOOST, combined with "
            "the learning poverty rate."
        ),
        "coverage_keys": ["boost", "learning_poverty_rate"],
    },
    "edu-opvcap": {
        "title": "Operational vs. Capital Spending",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    # ------------------------------------------------------------------
    # Education – Across Space
    # ------------------------------------------------------------------
    "edu-central-regional": {
        "title": "Centrally vs. Geographically Allocated Education Spending",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "edu-sub-func": {
        "title": "Education by Sub-functional Categories",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "edu-expenditure-map": {
        "title": "Education Expenditure Map",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "edu-outcome-map": {
        "title": "Education Outcomes Map",
        "source_name": "Global Data Lab",
        "coverage_keys": ["global_data_lab_hd_index"],
    },
    "edu-subnational": {
        "title": "Public Spending vs. Education Outcomes Across Regions",
        "source_name": "World Bank BOOST / Global Data Lab",
        "coverage_keys": ["boost", "global_data_lab_hd_index"],
    },
    # ------------------------------------------------------------------
    # Health – Over Time
    # ------------------------------------------------------------------
    "health-public-private": {
        "title": "Who Pays for Healthcare?",
        "source_name": "World Bank BOOST / WHO",
        "description": (
            "Public expenditure from BOOST. Out-of-pocket expenditure "
            "computed as CHE (current health expenditure in local "
            "currency) multiplied by OOP % of CHE, then adjusted for "
            "inflation using CPI. Source indicators: "
            "GHED_CHEGDP_SHA2011, GHED_OOPSCHE_SHA2011."
        ),
        "coverage_keys": ["boost", "health_private_expenditure"],
    },
    "health-total": {
        "title": "Total Health Expenditure",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "health-outcome": {
        "title": "Public Spending & Health Outcome",
        "source_name": "World Bank BOOST / WHO (GHO)",

        "description": (
            "Public health expenditure from BOOST, combined with the "
            "Universal Health Coverage service coverage index."
        ),
        "coverage_keys": ["boost", "universal_health_coverage_index_gho"],
    },
    "health-opvcap": {
        "title": "Operational vs. Capital Spending",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    # ------------------------------------------------------------------
    # Health – Across Space
    # ------------------------------------------------------------------
    "health-central-regional": {
        "title": "Centrally vs. Geographically Allocated Health Spending",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "health-sub-func": {
        "title": "Health by Sub-functional Categories",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "health-expenditure-map": {
        "title": "Health Expenditure Map",
        "source_name": "World Bank BOOST",
        "coverage_keys": ["boost"],
    },
    "health-outcome-map": {
        "title": "Health Outcomes Map",
        "source_name": "WHO (GHO)",

        "coverage_keys": ["universal_health_coverage_index_gho"],
    },
    "health-subnational": {
        "title": "Public Spending vs. Health Outcomes Across Regions",
        "source_name": "World Bank BOOST / WHO (GHO)",

        "coverage_keys": ["boost", "universal_health_coverage_index_gho"],
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
            "\u24D8",  # circled information source
            id={"type": "source-info-btn", "index": index},
            color="link",
            size="sm",
            style={
                "padding": "0 4px",
                "fontSize": "18px",
                "color": "#6c757d",
                "verticalAlign": "middle",
                "textDecoration": "none",
            },
        ),
        style={"marginLeft": "8px"},
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


def build_modal_children(info):
    """
    Build [ModalHeader, ModalBody] for a chart info modal.

    ``info`` is a dict from :data:`CHART_METADATA` augmented with
    ``country_name`` and ``coverage_lines`` by the callback.
    """
    title = info.get("title", "Source Details")
    description = info.get("description")
    source_name = info.get("source_name")
    framework_url = info.get("framework_url")
    coverage_lines = info.get("coverage_lines", [])

    body = []

    if description:
        body.append(
            html.P(description, style={"color": "#555", "marginBottom": "12px",
                                        "fontSize": "0.9rem"})
        )

    # Source attribution
    if source_name:
        body.append(_make_detail_row("Source", html.Span(source_name)))

    # Framework link
    if framework_url:
        link = html.A(
            framework_url,
            href=framework_url,
            target="_blank",
            rel="noopener noreferrer",
            style={"wordBreak": "break-all"},
        )
        body.append(_make_detail_row("Framework", link))

    # Coverage years
    if coverage_lines:
        body.append(
            _make_detail_row("Coverage", html.Span(", ".join(coverage_lines)))
        )

    return [
        dbc.ModalHeader(dbc.ModalTitle(title), close_button=True),
        dbc.ModalBody(body),
    ]


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
