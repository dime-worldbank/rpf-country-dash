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
    "world_bank_lpgd": {"label_key": "source.learning_poverty.label",    "publisher_key": "source.publisher.world_bank",       "name_key": "source.name.world_bank_lpgd", "description_key": None,                              "coverage_key": "learning_poverty_rate",                 "countries": None},
    "who_gho":         {"label_key": "source.uhc.label",                 "publisher_key": "source.publisher.who",              "name_key": "source.name.who_gho",         "description_key": None,                              "coverage_key": "universal_health_coverage_index_gho",   "countries": None},
    "who_nha":         {"label_key": "source.health_private.label",      "publisher_key": "source.publisher.who",              "name_key": "source.name.who_nha",         "description_key": "source.health_private.description", "coverage_key": "health_private_expenditure",          "countries": None},
    "pefa":            {"label_key": "source.pefa.label",                "publisher_key": "source.publisher.pefa_secretariat", "name_key": "source.name.pefa",            "description_key": "source.pefa.description",         "coverage_key": "pefa_by_pillar",                        "countries": None},
    "global_data_lab": {"label_key": "source.hd_index.label",            "publisher_key": "source.publisher.global_data_lab",  "name_key": "source.name.global_data_lab", "description_key": None,                              "coverage_key": "global_data_lab_hd_index",              "countries": None},
    # Subnational population sources. Only the non-default keys are listed; every
    # omitted key falls back in code (publisher/name → source_registry facts,
    # description → none, countries → all — the bridge does country scoping now).
    "census_gov":                {"label_key": "source.subnational_population.label", "coverage_key": "subnational_population"},
    "wb_subnational_population": {"label_key": "source.subnational_population.label", "coverage_key": "subnational_population"},
    "alb_instat":                {"label_key": "source.subnational_population.label", "coverage_key": "subnational_population"},
    "moz_ine":                   {"label_key": "source.subnational_population.label", "coverage_key": "subnational_population"},
    "pry_ine":                   {"label_key": "source.subnational_population.label", "coverage_key": "subnational_population"},
}

# Sentinel so a slot can distinguish "not overridden" from "overridden to None".
_UNSET = object()


def source_display_name(source_id, lang="en"):
    """Localized "publisher — name" for a source_id, shared by popover and narratives."""
    display = SOURCE_DISPLAY.get(source_id, {})
    publisher = t(display["publisher_key"], lang) if display.get("publisher_key") else ""
    name = t(display["name_key"], lang) if display.get("name_key") else ""
    return f"{publisher} — {name}" if publisher and name else (publisher or name)


def _registry_lookup(source_id, source_meta):
    """Return the source_registry record for source_id, or an empty dict."""
    for row in (source_meta or {}).get("source_registry", []):
        if row.get("source_id") == source_id:
            return row
    return {}


def _sources_for_indicator(indicator_key, source_meta, country=None):
    """Source id(s) feeding an indicator, resolved via the indicator_source bridge
    (order preserved). A multi-source indicator yields several source sections.

    A bridge row's country_name scopes it to one country; NULL/absent applies to all.
    subnational_population uses this — each country's admin1 population comes from a
    different source (census.gov, WB, Global Data Lab, national offices)."""
    sources = []
    for r in (source_meta or {}).get("indicator_source", []):
        if r.get("indicator_key") != indicator_key:
            continue
        row_country = r.get("country_name")
        if row_country and row_country != country:
            continue
        sources.append(r["source_id"])
    return sources


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
# Chart-level metadata for the ⓘ info buttons, keyed by chart ID.
# Each chart lists the indicator_key(s) it shows; the source(s) are resolved at
# runtime via the indicator_source bridge (a multi-source indicator yields several
# sections). An entry is a bare indicator_key string, or a dict
# {"indicator_key": ..., "label_key": ...} when the heading needs to be
# chart-specific (e.g. BOOST shown as education vs health expenditure).
# ``info_key`` adds a chart-level intro paragraph above the sections.
# ---------------------------------------------------------------------------
# Chart-specific BOOST headings (same boost pseudo-indicator, different metric label).
_BOOST_EDU = {"indicator_key": "boost", "label_key": "source.boost_edu.label"}
_BOOST_HEALTH = {"indicator_key": "boost", "label_key": "source.boost_health.label"}

CHART_METADATA = {
    # ------------------------------------------------------------------
    # Home – Over Time
    # ------------------------------------------------------------------
    "overview-total": {"indicators": ["boost"]},
    "overview-per-capita": {"indicators": ["boost", "poverty_rate"]},
    "functional-breakdown": {"indicators": ["boost"]},
    "func-growth": {"indicators": ["boost"]},
    "economic-breakdown": {"indicators": ["boost"]},
    "pefa-overall": {"indicators": ["pefa_by_pillar", "poverty_rate"]},
    "pefa-by-pillar": {"indicators": ["pefa_by_pillar"]},
    "revenue-expenditure-combined": {
        "info_key": "chart.revenue_expenditure_combined.info",
        # Used when the official national report (togo_revenue_budget) isn't shown
        # for the country — then there's no composite, just GFS/WEO views.
        "info_key_fallback": "chart.revenue_expenditure_combined.info_imf",
        # Shared panel legend appended to whichever intro applies.
        "info_suffix_key": "chart.revenue_expenditure_combined.panels",
        "info_primary_indicator": "togo_revenue_budget",
        "indicators": ["togo_revenue_budget", "government_revenue_expenditure"],
    },
    # ------------------------------------------------------------------
    # Home – Across Space
    # ------------------------------------------------------------------
    "subnational-spending": {"indicators": [
        "boost",
        # One heading for whichever per-country source the bridge resolves (census.gov,
        # WB, Global Data Lab, national offices) — overrides each source's own label
        # (e.g. Global Data Lab's HDI label) in this population context.
        {"indicator_key": "subnational_population", "label_key": "source.subnational_population.label"},
    ]},
    "subnational-poverty": {"indicators": ["subnational_poverty_rate"]},
    # ------------------------------------------------------------------
    # Education – Over Time
    # ------------------------------------------------------------------
    "education-public-private": {"indicators": [_BOOST_EDU, "edu_private_expenditure"]},
    "education-total": {"indicators": ["boost"]},
    "education-outcome": {"indicators": [
        _BOOST_EDU,
        "learning_poverty_rate",
        {"indicator_key": "global_data_lab_attendance", "label_key": "source.attendance.label"},
    ]},
    "econ-breakdown-func-edu": {"indicators": ["boost"]},
    # ------------------------------------------------------------------
    # Education – Across Space
    # ------------------------------------------------------------------
    "education-central-vs-regional": {"indicators": ["boost"]},
    "education-sub-func": {"indicators": ["boost"]},
    "education-expenditure-map": {"indicators": ["boost"]},
    "education-outcome-map": {"indicators": ["global_data_lab_hd_index"]},
    "education-subnational": {"indicators": [_BOOST_EDU, "global_data_lab_hd_index"]},
    # ------------------------------------------------------------------
    # Health – Over Time
    # ------------------------------------------------------------------
    "health-public-private": {"indicators": [_BOOST_HEALTH, "health_private_expenditure"]},
    "health-total": {"indicators": ["boost"]},
    "health-outcome": {"indicators": [_BOOST_HEALTH, "universal_health_coverage_index_gho"]},
    "econ-breakdown-func-health": {"indicators": ["boost"]},
    # ------------------------------------------------------------------
    # Health – Across Space
    # ------------------------------------------------------------------
    "health-central-vs-regional": {"indicators": ["boost"]},
    "health-sub-func": {"indicators": ["boost"]},
    "health-expenditure-map": {"indicators": ["boost"]},
    "health-outcome-map": {"indicators": ["universal_health_coverage_index_gho"]},
    "health-subnational": {"indicators": [_BOOST_HEALTH, "universal_health_coverage_index_gho"]},
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


def _group_sections(sections):
    """Group sections that describe the same metric (identical heading,
    methodology, and coverage) so a multi-source indicator renders those shared
    fields once. Order of first appearance is preserved."""
    groups = []
    seen = {}
    for section in sections:
        key = (section.get("label"), section.get("description"), section.get("coverage"))
        if key in seen:
            groups[seen[key]].append(section)
        else:
            seen[key] = len(groups)
            groups.append([section])
    return groups


def _build_source_section(sections, country_name=None, lang="en"):
    """Build the Dash components for one metric.

    ``sections`` is a list of source sections sharing heading, methodology, and
    coverage (a single-source metric is a one-element list). The heading,
    methodology, and coverage render once; the More-info and Source rows repeat
    per source in order.
    """
    first = sections[0]
    children = [html.H6(first.get("label", ""), className="source-section-heading")]

    # Metric-level context (shared across the metric's sources): coverage, then
    # methodology. Methodology sits last of the shared rows so it stays adjacent
    # to the source list it often names (e.g. subnational poverty ← SPID + GSAP).
    coverage = first.get("coverage")
    if coverage:
        label = (
            t("detail.coverage_for", lang, country=t(f"country.{country_name}", lang))
            if country_name
            else t("detail.coverage", lang)
        )
        children.append(_make_detail_row(label, html.Span(coverage)))

    desc = first.get("description")
    if desc:
        children.append(_make_detail_row(t("detail.methodology", lang), html.Span(desc)))

    # Source name + its More-info link, repeated per contributing source
    for section in sections:
        source_name = section.get("source_name")
        if source_name:
            children.append(_make_detail_row(t("detail.source", lang), html.Span(source_name)))

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

    # Per-metric sections. Sources feeding the same metric (identical heading,
    # methodology, coverage) render those shared fields once and repeat only the
    # More-info/Source rows per source.
    for group in _group_sections(source_sections):
        body.append(_build_source_section(group, country_name=info.get("country_name"), lang=lang))

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
    Return the ``(start_year, end_year)`` span to display for a coverage key and
    country, or ``(None, None)``.

    *coverage_key* is either ``"boost"`` (span from boost_source_urls) or an
    indicator_key (discrete ``years`` from indicator_availability). Keyed by
    indicator (not source) so a source feeding several indicators still resolves
    to the precise span of the indicator shown in this chart slot.

    START_YEAR is the dashboard's display floor: BOOST clamps its start to it, and
    an indicator's span is taken over its data years >= START_YEAR — so the start
    is the first real data year in view, not an older survey year floored up.
    """
    if not country or not source_meta:
        return None, None

    if coverage_key == "boost":
        for row in source_meta.get("boost_source_urls", []):
            if row.get("country_name") == country:
                start = row.get("earliest_year")
                end = row.get("latest_year")
                start = max(int(start), START_YEAR) if start else None
                end = int(end) if end else None
                return start, end
        return None, None

    for row in source_meta.get("indicator_availability", []):
        if row.get("country_name") == country and row.get("indicator_key") == coverage_key:
            years = sorted(
                int(y) for y in (row.get("years") or []) if y is not None and int(y) >= START_YEAR
            )
            return (years[0], years[-1]) if years else (None, None)

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

    # Bridge-driven: the chart lists indicator_key(s); each resolves to its
    # source(s) via the indicator_source bridge (a multi-source indicator
    # yields several sections). Coverage tracks the indicator; an optional
    # per-entry label_key overrides the heading (e.g. BOOST's chart context).
    source_sections = []
    rendered_indicators = set()
    for entry in chart_meta.get("indicators", []):
        ind_key = entry if isinstance(entry, str) else entry["indicator_key"]
        label_key = None if isinstance(entry, str) else entry.get("label_key")
        for source_id in _sources_for_indicator(ind_key, source_meta, country):
            slot = {"source_id": source_id, "coverage_key": ind_key}
            if label_key:
                slot["label_key"] = label_key
            section = _resolve_source_section(slot, country, source_meta, lang)
            if section is not None:
                source_sections.append(section)
                rendered_indicators.add(ind_key)

    # A chart may vary its intro by whether a priority source actually renders for
    # this country: the revenue/expenditure composite only describes the official
    # national report when one exists, and falls back to the IMF-only wording
    # otherwise, so it never describes sources that aren't shown.
    info_key = chart_meta.get("info_key")
    primary = chart_meta.get("info_primary_indicator")
    if primary and primary not in rendered_indicators:
        info_key = chart_meta.get("info_key_fallback", info_key)
    info = t(info_key, lang) if info_key else None
    # Shared trailing text (e.g. the panel legend) is appended to whichever intro
    # was chosen, so the intro variants don't each repeat it.
    suffix_key = chart_meta.get("info_suffix_key")
    if info and suffix_key:
        info = f"{info} {t(suffix_key, lang)}"

    return {
        **chart_meta,
        "_index": chart_id,
        "country_name": country,
        "source_sections": source_sections,
        "info": info,
    }
