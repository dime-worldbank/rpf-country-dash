import pandas as pd
from dash import html
import dash_bootstrap_components as dbc

from constants import START_YEAR
from translations import t


# ---------------------------------------------------------------------------
# Source presentation, keyed by source_id. Facts (name/publisher/url) come from
# the pipeline's source_registry; only i18n keys and per-source country scoping
# live here. Each source has defaults that a chart slot may override:
#   - label_key       : section heading (a chart slot often overrides this to a
#                       chart-specific metric label, e.g. "Public Health Expenditure")
#   - publisher_key   : shared org key (e.g. source.publisher.world_bank)
#   - name_key        : per-source dataset name key ("" suppresses → publisher only)
#   - description_key : methodology text (optional)
#   - coverage_key    : the indicator_key (or "boost") whose year span this source
#                       shows; a slot overrides it when a source feeds >1 indicator
#   - countries       : whitelist; the source is hidden for other countries
# The "Source:" line renders as "publisher — name" (both localized).
# ---------------------------------------------------------------------------

SOURCE_DISPLAY = {
    "boost":           {"label_key": "source.boost.label",               "publisher_key": "source.publisher.world_bank",       "name_key": "source.name.boost",           "description_key": None,                              "coverage_key": "boost",                                 "countries": None},
    "imf_weo":         {"label_key": "source.imf_weo.label",             "publisher_key": "source.publisher.imf",              "name_key": "source.name.imf_weo",         "description_key": "source.imf_weo.description",      "coverage_key": "government_revenue_expenditure",        "countries": None},
    "imf_gfs":         {"label_key": "source.imf_gfs.label",             "publisher_key": "source.publisher.imf",              "name_key": "source.name.imf_gfs",         "description_key": "source.imf_gfs.description",      "coverage_key": "government_revenue_expenditure",        "countries": None},
    "togo_dgb":        {"label_key": "source.togo_dgb.label",            "publisher_key": "source.publisher.togo_dgb",         "name_key": "source.name.togo_dgb",        "description_key": "source.togo_dgb.description",     "coverage_key": "togo_revenue_budget",                   "countries": ["Togo"]},
    "world_bank_pip":  {"label_key": "source.poverty_rate.label",        "publisher_key": "source.publisher.world_bank",       "name_key": "source.name.world_bank_pip",  "description_key": "source.poverty_rate.description", "coverage_key": "poverty_rate",                          "countries": None},
    "pip_spid":        {"label_key": "source.subnational_poverty.label", "publisher_key": "source.publisher.world_bank",       "name_key": "source.name.pip_spid",        "description_key": "source.subnational_poverty.description", "coverage_key": "subnational_poverty_rate",       "countries": None},
    "pip_gsap":        {"label_key": "source.subnational_poverty.label", "publisher_key": "source.publisher.world_bank",       "name_key": "source.name.pip_gsap",        "description_key": "source.subnational_poverty.description", "coverage_key": "subnational_poverty_rate",       "countries": None},
    "world_bank_icp":  {"label_key": "source.edu_private.label",         "publisher_key": "source.publisher.world_bank",       "name_key": "source.name.world_bank_icp",  "description_key": "source.edu_private.description",  "coverage_key": "edu_private_expenditure",               "countries": None},
    "unesco_uis":      {"label_key": "source.learning_poverty.label",    "publisher_key": "source.publisher.unesco",           "name_key": "source.name.unesco_uis",      "description_key": None,                              "coverage_key": "learning_poverty_rate",                 "countries": None},
    "who_gho":         {"label_key": "source.uhc.label",                 "publisher_key": "source.publisher.who",              "name_key": "source.name.who_gho",         "description_key": None,                              "coverage_key": "universal_health_coverage_index_gho",   "countries": None},
    "who_nha":         {"label_key": "source.health_private.label",      "publisher_key": "source.publisher.who",              "name_key": "source.name.who_nha",         "description_key": "source.health_private.description", "coverage_key": "health_private_expenditure",          "countries": None},
    "pefa":            {"label_key": "source.pefa.label",                "publisher_key": "source.publisher.pefa_secretariat", "name_key": "source.name.pefa",            "description_key": "source.pefa.description",         "coverage_key": "pefa_by_pillar",                        "countries": None},
    "global_data_lab": {"label_key": "source.hd_index.label",            "publisher_key": "source.publisher.global_data_lab",  "name_key": "source.name.global_data_lab", "description_key": None,                              "coverage_key": "global_data_lab_hd_index",              "countries": None},
}

# Sentinel so a slot can distinguish "not overridden" from "overridden to None".
_UNSET = object()


def _registry_lookup(source_id, source_meta):
    """Return the source_registry record for source_id, or an empty dict."""
    for row in (source_meta or {}).get("source_registry", []):
        if row.get("source_id") == source_id:
            return row
    return {}


def _resolve_url(source_id, country, source_meta, registry):
    """boost keeps its per-country URL; every other source uses registry.url."""
    if source_id == "boost":
        for row in (source_meta or {}).get("boost_source_urls", []):
            if row.get("country_name") == country and row.get("source_url"):
                return row["source_url"]
    return registry.get("url")


def _resolve_source_section(slot, country, source_meta, lang="en"):
    """Build a source section dict from a chart slot, or None when the source is
    scoped to other countries.

    ``slot`` is ``{"source_id": ..., **overrides}``. Overrides (label_key,
    publisher_key, name_key, description_key, coverage_key) fall back to
    SOURCE_DISPLAY defaults, then to source_registry facts. ``name_key: ""``
    suppresses the dataset name so the Source line is the publisher alone.
    """
    source_id = slot["source_id"]
    display = SOURCE_DISPLAY.get(source_id, {})

    scoped = display.get("countries")
    if scoped and country not in scoped:
        return None

    registry = _registry_lookup(source_id, source_meta)

    label_key = slot.get("label_key", display.get("label_key"))
    publisher_key = slot.get("publisher_key", display.get("publisher_key"))
    name_key = slot.get("name_key", display.get("name_key", _UNSET))
    description_key = slot.get("description_key", display.get("description_key"))
    coverage_key = slot.get("coverage_key", display.get("coverage_key"))

    publisher = t(publisher_key, lang) if publisher_key else registry.get("publisher", "")
    if name_key == "":
        name = ""  # explicit suppression → publisher-only Source line
    elif name_key and name_key is not _UNSET:
        name = t(name_key, lang)
    else:
        name = registry.get("name", "")
    source_name = f"{publisher} — {name}" if publisher and name else (publisher or name)

    section = {
        "label": t(label_key, lang) if label_key else name,
        "source_name": source_name,
        "description": t(description_key, lang) if description_key else None,
        "source_url": _resolve_url(source_id, country, source_meta, registry),
    }
    start, end = get_coverage_years(coverage_key, country, source_meta) if coverage_key else (None, None)
    if start and end:
        section["coverage"] = f"{start}–{end}"
    return section


# ---------------------------------------------------------------------------
# Chart-level metadata for the ⓘ info buttons.
# Keyed by chart ID (matches the ``index`` used in ``source_info_button``).
# Each source is a slot: a bare ``source_id`` string (uses SOURCE_DISPLAY
# defaults) or a dict ``{"source_id": ..., **overrides}`` when a chart needs a
# specific heading (``label_key``) or, for a source feeding several indicators,
# a specific ``coverage_key``. Dynamic per-country coverage years are merged at
# runtime. ``info_key`` adds a chart-level intro paragraph above the sections.
# ---------------------------------------------------------------------------
# Chart-specific boost headings (same boost source, different metric label).
_BOOST_EDU = {"source_id": "boost", "label_key": "source.boost_edu.label"}
_BOOST_HEALTH = {"source_id": "boost", "label_key": "source.boost_health.label"}

CHART_METADATA = {
    # ------------------------------------------------------------------
    # Home – Over Time
    # ------------------------------------------------------------------
    "overview-total": {"sources": ["boost"]},
    "overview-per-capita": {"sources": ["boost", "world_bank_pip"]},
    "functional-breakdown": {"sources": ["boost"]},
    "func-growth": {"sources": ["boost"]},
    "economic-breakdown": {"sources": ["boost"]},
    "pefa-overall": {"sources": ["pefa", "world_bank_pip"]},
    "pefa-by-pillar": {"sources": ["pefa"]},
    "revenue-expenditure-combined": {
        "info_key": "chart.revenue_expenditure_combined.info",
        "sources": ["togo_dgb", "imf_gfs", "imf_weo"],
    },
    # ------------------------------------------------------------------
    # Home – Across Space
    # ------------------------------------------------------------------
    "subnational-spending": {"sources": ["boost"]},
    "subnational-poverty": {"sources": ["pip_spid", "pip_gsap"]},
    # ------------------------------------------------------------------
    # Education – Over Time
    # ------------------------------------------------------------------
    "education-public-private": {"sources": [_BOOST_EDU, "world_bank_icp"]},
    "education-total": {"sources": ["boost"]},
    "education-outcome": {"sources": [
        _BOOST_EDU,
        # Learning poverty is attributed to World Bank alone (name suppressed);
        # coverage tracks the learning_poverty_rate indicator.
        {"source_id": "world_bank_pip", "label_key": "source.learning_poverty.label",
         "coverage_key": "learning_poverty_rate", "name_key": ""},
        {"source_id": "global_data_lab", "label_key": "source.attendance.label",
         "coverage_key": "global_data_lab_attendance"},
    ]},
    "econ-breakdown-func-edu": {"sources": ["boost"]},
    # ------------------------------------------------------------------
    # Education – Across Space
    # ------------------------------------------------------------------
    "education-central-vs-regional": {"sources": ["boost"]},
    "education-sub-func": {"sources": ["boost"]},
    "education-expenditure-map": {"sources": ["boost"]},
    "education-outcome-map": {"sources": ["global_data_lab"]},
    "education-subnational": {"sources": [_BOOST_EDU, "global_data_lab"]},
    # ------------------------------------------------------------------
    # Health – Over Time
    # ------------------------------------------------------------------
    "health-public-private": {"sources": [_BOOST_HEALTH, "who_nha"]},
    "health-total": {"sources": ["boost"]},
    "health-outcome": {"sources": [_BOOST_HEALTH, "who_gho"]},
    "econ-breakdown-func-health": {"sources": ["boost"]},
    # ------------------------------------------------------------------
    # Health – Across Space
    # ------------------------------------------------------------------
    "health-central-vs-regional": {"sources": ["boost"]},
    "health-sub-func": {"sources": ["boost"]},
    "health-expenditure-map": {"sources": ["boost"]},
    "health-outcome-map": {"sources": ["who_gho"]},
    "health-subnational": {"sources": [_BOOST_HEALTH, "who_gho"]},
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
            t("detail.coverage_for", lang, country=t(f"country.{country_name}", lang))
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

    # Chart-level intro paragraph (optional) — appears once above all sources
    chart_info = info.get("info")
    if chart_info:
        body.append(
            html.P(chart_info, className="rpf-chart-info", style={"fontStyle": "italic"})
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

def get_coverage_years(coverage_key, country, source_meta):
    """
    Return ``(earliest_year, latest_year)`` for a coverage key and country.

    *coverage_key* is either ``"boost"`` (looks up from boost_source_urls) or an
    indicator_key such as ``"pefa_by_pillar"`` (looks up from indicator_availability).
    Keyed by indicator (not source) so a source feeding several indicators still
    resolves to the precise span of the indicator shown in this chart slot.
    """
    if not country or not source_meta:
        return None, None

    # Select the appropriate data source
    rows = (
        source_meta.get("boost_source_urls", [])
        if coverage_key == "boost"
        else source_meta.get("indicator_availability", [])
    )

    # Find matching row
    for row in rows:
        if row.get("country_name") == country and (
            coverage_key == "boost" or row.get("indicator_key") == coverage_key
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
        source_meta: Dict with "source_registry", "boost_source_urls", and
                     "indicator_availability" from stored data
        lang: Language code ("en", "fr", "pt") for translated labels/descriptions

    Returns:
        Dict with chart metadata, index, country, and source sections
    """
    chart_meta = CHART_METADATA.get(chart_id, {})

    source_sections = []
    for entry in chart_meta.get("sources", []):
        slot = {"source_id": entry} if isinstance(entry, str) else entry
        section = _resolve_source_section(slot, country, source_meta, lang)
        if section is not None:
            source_sections.append(section)

    info_key = chart_meta.get("info_key")
    return {
        **chart_meta,
        "_index": chart_id,
        "country_name": country,
        "source_sections": source_sections,
        "info": t(info_key, lang) if info_key else None,
    }
