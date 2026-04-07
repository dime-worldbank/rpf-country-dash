import pandas as pd
from dash import html
import dash_bootstrap_components as dbc

from constants import START_YEAR
from translations import t


# ---------------------------------------------------------------------------
# Shared source definitions – define once, reuse across charts.
#
# Each source has three i18n reference fields:
#   - label_key        : per-source label (e.g. "source.boost_edu.label")
#   - source_name_key  : shared across sources (e.g. "source_name.world_bank_boost")
#   - description_key  : per-source methodology text (optional)
#
# The "key" field is the coverage/data-lookup key used to fetch coverage years
# and source URLs from the pipeline.
# ---------------------------------------------------------------------------

_BOOST = {
    "key": "boost",
    "label_key": "source.boost.label",
    "source_name_key": "source_name.world_bank_boost",
    "source_url": "https://www.worldbank.org/en/programs/boost-portal/country-data",
}
_BOOST_EDU = {**_BOOST, "label_key": "source.boost_edu.label"}
_BOOST_HEALTH = {**_BOOST, "label_key": "source.boost_health.label"}

_POVERTY_RATE = {
    "key": "poverty_rate",
    "label_key": "source.poverty_rate.label",
    "source_name_key": "source_name.world_bank_pip",
    "description_key": "source.poverty_rate.description",
}

_SUBNATIONAL_POVERTY = {
    "key": "subnational_poverty_rate",
    "label_key": "source.subnational_poverty.label",
    "source_name_key": "source_name.world_bank",
    "description_key": "source.subnational_poverty.description",
}

_LEARNING_POVERTY = {
    "key": "learning_poverty_rate",
    "label_key": "source.learning_poverty.label",
    "source_name_key": "source_name.world_bank",
}

_HD_INDEX = {
    "key": "global_data_lab_hd_index",
    "label_key": "source.hd_index.label",
    "source_name_key": "source_name.global_data_lab",
}

_ATTENDANCE = {
    "key": "global_data_lab_attendance",
    "label_key": "source.attendance.label",
    "source_name_key": "source_name.global_data_lab",
}

_UHC = {
    "key": "universal_health_coverage_index_gho",
    "label_key": "source.uhc.label",
    "source_name_key": "source_name.who_gho",
}

_PEFA = {
    "key": "pefa_by_pillar",
    "label_key": "source.pefa.label",
    "source_name_key": "source_name.pefa_secretariat",
    "description_key": "source.pefa.description",
}

_EDU_PRIVATE = {
    "key": "edu_private_expenditure",
    "label_key": "source.edu_private.label",
    "source_name_key": "source_name.world_bank_icp",
    "description_key": "source.edu_private.description",
    "source_url": "https://www.worldbank.org/en/programs/icp/data",
}

_HEALTH_PRIVATE = {
    "key": "health_private_expenditure",
    "label_key": "source.health_private.label",
    "source_name_key": "source_name.who_health_db",
    "description_key": "source.health_private.description",
    "source_url": "https://apps.who.int/nha/database/",
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
        className="source-info-btn",
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
        className="source-info-chart-container",
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


def _build_source_section(section, country_name=None, lang="en"):
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
        children.append(_make_detail_row(t("detail.methodology", lang), html.Span(desc)))

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
        children.append(_make_detail_row(t("detail.more_info", lang), link))

    # Source name
    source_name = section.get("source_name")
    if source_name:
        children.append(_make_detail_row(t("detail.source", lang), html.Span(source_name)))

    # Coverage years
    coverage = section.get("coverage")
    if coverage:
        label = (
            t("detail.coverage_for", lang, country=country_name)
            if country_name
            else t("detail.coverage", lang)
        )
        children.append(_make_detail_row(label, html.Span(coverage)))

    return html.Div(children, className="rpf-source-section")


def build_modal_children(info, lang="en"):
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
                className="source-info-close-btn",
            ),
            className="source-info-close-wrapper",
        )
    )

    # Per-source sections
    for section in source_sections:
        body.append(_build_source_section(section, country_name=info.get("country_name"), lang=lang))

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

def get_coverage_years(key, country, source_meta):
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


def build_modal_info(chart_id, country, source_meta, lang="en"):
    """
    Build the complete info dict for the modal.

    Fetches chart metadata, builds source sections with coverage years
    and URLs, and returns the complete info structure.

    Args:
        chart_id: Chart key from CHART_METADATA
        country: Selected country name
        source_meta: Dict with "boost_source_urls", "indicator_availability",
                     and "source_urls_by_country" from stored data
        lang: Language code ("en", "fr") for translated labels/descriptions

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
        description_key = src.get("description_key")
        section = {
            "label": t(src["label_key"], lang),
            "source_name": t(src["source_name_key"], lang),
            "description": t(description_key, lang) if description_key else None,
        }

        # Coverage years
        start, end = get_coverage_years(key, country, source_meta)
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
