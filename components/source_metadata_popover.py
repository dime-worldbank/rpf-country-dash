import pandas as pd
from dash import html
import dash_bootstrap_components as dbc


# Maps each button index to the source_key(s) used for metadata lookup.
# Values are either a single string or a list of strings for charts that
# combine multiple data sources.
# Used by the single MATCH callback in app.py.
BUTTON_SOURCE_MAP = {
    # Home – Over Time
    "home-total-exp": "boost",
    "home-percapita-exp": "boost",
    "home-func-breakdown": "boost",
    "home-func-growth": "boost",
    "home-econ-breakdown": "boost",
    "home-pefa-overall": ["pefa_by_pillar", "subnational_poverty_rate"],
    "home-pefa-pillar": ["pefa_by_pillar"],
    # Home – Across Space
    "home-regional-spending": "boost",
    "home-regional-poverty": "subnational_poverty_rate",
    # Education – Over Time
    "edu-public-private": ["boost", "edu_private_expenditure"],
    "edu-total": "boost",
    "edu-outcome": ["boost", "learning_poverty_rate",],
    "edu-opvcap": "boost",
    # Education – Across Space
    "edu-central-regional": "boost",
    "edu-sub-func": "boost",
    "edu-expenditure-map": "boost",
    "edu-outcome-map": "global_data_lab_hd_index",
    "edu-subnational": ["boost", "global_data_lab_hd_index"],
    # Health – Over Time
    "health-public-private": ["boost", "health_private_expenditure"],
    "health-total": "boost",
    "health-outcome": ["boost", "universal_health_coverage_index_gho"],
    "health-opvcap": "boost",
    # Health – Across Space
    "health-central-regional": "boost",
    "health-sub-func": "boost",
    "health-expenditure-map": "boost",
    "health-outcome-map": "universal_health_coverage_index_gho",
    "health-subnational": ["boost", "universal_health_coverage_index_gho"],
}


def source_info_button(index):
    """Renders a small circular info button with an (i) icon.

    ``index`` is a short key such as ``"overview-boost"`` that appears in
    :data:`BUTTON_SOURCE_MAP`.  The component id is a dict so that a single
    Dash pattern-matching callback can service every button.
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


def _build_single_source_section(title, description=None, source_name=None,
                                  source_url=None, country_name=None,
                                  start_year=None, end_year=None):
    """Build body children for a single data source."""
    children = []

    children.append(
        html.H6(title or "Unknown Source",
                 style={"fontWeight": "bold", "marginBottom": "6px"})
    )

    if description:
        children.append(
            html.P(description, style={"color": "#555", "marginBottom": "8px",
                                        "fontSize": "0.9rem"})
        )

    if source_url:
        source_content = html.Span([
            html.Span(f"{source_name}, ") if source_name else "",
            html.A(
                source_url,
                href=source_url,
                target="_blank",
                rel="noopener noreferrer",
                style={"wordBreak": "break-all"},
            ),
        ])
    elif source_name:
        source_content = html.Span(source_name)
    else:
        source_content = None

    if source_content:
        children.append(_make_detail_row("Source", source_content))

    if start_year and end_year and country_name:
        coverage = f"{country_name}: {start_year}\u2013{end_year}"
        children.append(_make_detail_row("Coverage", coverage))

    return children


def build_modal_children(info):
    """
    Build the children list for a dbc.Modal given a single source info dict.

    ``info`` has keys: title, description, source_name, source_url,
    country_name, start_year, end_year.
    Returns [ModalHeader, ModalBody].
    """
    title = info.get("title") or info.get("source_key", "Source Details")

    body_children = _build_single_source_section(
        title=info.get("title"),
        description=info.get("description"),
        source_name=info.get("source_name"),
        source_url=info.get("source_url"),
        country_name=info.get("country_name"),
        start_year=info.get("start_year"),
        end_year=info.get("end_year"),
    )

    return [
        dbc.ModalHeader(dbc.ModalTitle(title), close_button=True),
        dbc.ModalBody(body_children),
    ]


def build_multi_source_modal_children(source_infos):
    """
    Build modal children for a chart with multiple data sources.

    ``source_infos`` is a list of dicts, each with keys:
        title, description, source_name, source_url,
        country_name, start_year, end_year
    """
    body_children = []
    for i, info in enumerate(source_infos):
        if i > 0:
            body_children.append(html.Hr(style={"margin": "12px 0"}))
        body_children.extend(
            _build_single_source_section(
                title=info.get("title"),
                description=info.get("description"),
                source_name=info.get("source_name"),
                source_url=info.get("source_url"),
                country_name=info.get("country_name"),
                start_year=info.get("start_year"),
                end_year=info.get("end_year"),
            )
        )

    return [
        dbc.ModalHeader(dbc.ModalTitle("Data Sources"), close_button=True),
        dbc.ModalBody(body_children),
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


def get_source_info(source_key, country, source_meta, expenditure_data=None):
    """
    Extract source metadata from the queried data stores.

    Returns a dict with keys: title, description, source_name, source_url,
    country_name, start_year, end_year.
    """
    result = {"source_key": source_key, "country_name": country}

    if not source_meta or not country:
        return result

    if source_key == "boost":
        # Look up from boost data availability table
        boost_rows = pd.DataFrame(source_meta.get("boost_source_urls", []))
        if not boost_rows.empty:
            match = boost_rows[boost_rows.country_name == country]
            if not match.empty:
                row = match.iloc[0]
                result["source_url"] = row.get("boost_source_url") or None
                result["title"] = row.get("boost_title")
                result["description"] = row.get("boost_description")
                result["source_name"] = row.get("boost_source_name")

        if expenditure_data:
            exp_df = pd.DataFrame(
                expenditure_data.get("expenditure_w_poverty_by_country_year", [])
            )
            country_df = (
                exp_df[exp_df.country_name == country]
                if not exp_df.empty else exp_df
            )
            if not country_df.empty:
                result["start_year"] = int(country_df.year.min())
                result["end_year"] = int(country_df.year.max())
    else:
        # Look up from indicator data availability table
        indicator_rows = pd.DataFrame(
            source_meta.get("indicator_availability", [])
        )
        if not indicator_rows.empty:
            match = indicator_rows[
                (indicator_rows.country_name == country)
                & (indicator_rows.indicator_key == source_key)
            ]
            if not match.empty:
                row = match.iloc[0]
                result["source_url"] = row.get("source_url") or None
                result["title"] = row.get("title")
                result["description"] = row.get("description")
                result["source_name"] = row.get("source_name")
                if pd.notna(row.get("start_year")):
                    result["start_year"] = int(row["start_year"])
                if pd.notna(row.get("end_year")):
                    result["end_year"] = int(row["end_year"])

    return result
