"""Reusable "spending by func-sub level + service-delivery indicator" section.

A spending-breakdown line chart (per-capita real spending by sub-functional
level, filterable by economic category) shown next to a service-delivery
indicator chart the user picks independently, plus a dynamic narrative.

The engine is sector-agnostic: every sector-specific piece (data store, level
model, indicator configs, ids, translation keys) lives in a :class:`SectionConfig`
that the caller passes in. ``EDU_CONFIG`` below is the Education instance; a
Health instance can be added the same way. Following the dashboard convention
this module holds the layout builder and pure helpers; the ``@callback``
wrappers live in the page and delegate here.
"""
from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import html

import server_store
from constants import START_YEAR, translate_econ
from translations import t
from utils import apply_locale, empty_plot, format_currency, millify
from viz_theme import QUALITATIVE
from components import econ_outcome_filter
from components.econ_outcome_filter import ALL_ECON
from components.source_metadata_popover import chart_container


@dataclass
class SectionConfig:
    """Everything sector-specific the engine needs (Education, Health, ...)."""
    # Component ids (shared between layout() and the page callbacks).
    econ_filter_id: str
    outcome_filter_id: str
    spending_chart_id: str
    outcome_chart_id: str
    narrative_id: str
    # Data
    store_key: str                 # spending frame: country_name, year, func_sub, econ, per_capita_real_expenditure
    func_sub_order: tuple          # func_sub values to plot, in display order
    func_sub_to_level: dict        # func_sub value -> canonical level key
    level_order: tuple             # canonical levels in display order (outcome chart)
    level_colors: dict             # canonical level -> color
    # Service-delivery indicators
    outcome_by_key: dict           # indicator key -> outcome column config
    outcome_options: tuple         # ((value, label_key), ...) for the dropdown
    default_outcome_key: str
    econ_default_outcome: dict     # econ value -> indicator key (category → default)
    # Translation keys
    heading_key: str
    chart_title_key: str


# Shared legend/margin so both charts' legend boxes match in placement & style.
_LEGEND_STYLE = dict(
    orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5,
    font=dict(size=11),
)
_CHART_MARGIN = dict(l=20, r=20, t=50, b=80)


# ---------------------------------------------------------------------------
# Helpers (sector-agnostic)
# ---------------------------------------------------------------------------
def _year_axis_ticks(years):
    """Return (tick0, dtick) that keep year-axis ticks on whole years.

    A plain linear axis with few points lets Plotly pick a fractional dtick
    (e.g. 0.5), which ``tickformat="d"`` then rounds to repeated year labels.
    Forcing an integer dtick (~10 ticks max) avoids the duplicates.
    """
    years = [int(y) for y in years]
    if not years:
        return 0, 1
    span = max(years) - min(years)
    dtick = max(1, round(span / 10)) if span else 1
    return min(years), dtick


def _shared_year_range(config, country, econ_filter):
    """[min, max] year range for the x-axis, derived from the spending data only,
    floored at START_YEAR. Both charts use it so they share one x-axis — and,
    crucially, the outcome indicator does NOT influence it, so switching
    indicators never moves the spending chart. Returns None if no spending data.
    """
    breakdown = server_store.get(config.store_key)
    breakdown = breakdown[
        (breakdown["country_name"] == country)
        & (breakdown["func_sub"].isin(config.func_sub_order))
    ]
    if econ_filter and econ_filter != ALL_ECON:
        breakdown = breakdown[breakdown["econ"] == econ_filter]

    years = breakdown["year"].tolist()
    if not years:
        return None
    years = [int(y) for y in years]
    lo, hi = max(min(years), START_YEAR), max(years)
    return (lo, hi) if lo <= hi else None


def _apply_shared_xaxis(config, fig, country, econ_filter):
    """Apply the spending-derived shared x-axis (whole-year ticks + range)."""
    year_range = _shared_year_range(config, country, econ_filter)
    if year_range:
        lo, hi = year_range
        tick0, dtick = _year_axis_ticks([lo, hi])
        fig.update_xaxes(
            tickformat="d", tick0=tick0, dtick=dtick, range=[lo - 0.5, hi + 0.5]
        )
    else:
        fig.update_xaxes(tickformat="d")


def _finalize(fig, title, lang):
    """Shared layout (hover, legend, margin) + locale, common to both charts."""
    fig.update_layout(
        hovermode="x unified",
        title=title,
        plot_bgcolor="white",
        legend=_LEGEND_STYLE,
        margin=_CHART_MARGIN,
    )
    return apply_locale(fig, lang)


# ---------------------------------------------------------------------------
# Callback delegates (pure functions; the @callbacks live in the page module)
# ---------------------------------------------------------------------------
def econ_filter_options(config, country, lang, current_value):
    """(options, value) for the economic-category dropdown, per country."""
    return econ_outcome_filter.econ_options(
        config.store_key, country, lang, current_value
    )


def default_outcome_indicator(config, econ_filter):
    """The natural service-delivery indicator for a selected economic category."""
    return econ_outcome_filter.default_indicator(
        econ_filter, config.econ_default_outcome, config.default_outcome_key
    )


def spending_figure(config, country, econ_filter, basic_country_data, lang="en"):
    """Per-capita real spending by level, filtered by economic category."""
    lang = lang or "en"
    if not country:
        return empty_plot(t("loading", lang))

    df = server_store.get(config.store_key)
    df = df[
        (df["country_name"] == country)
        & (df["func_sub"].isin(config.func_sub_order))
    ]
    if econ_filter and econ_filter != ALL_ECON:
        df = df[df["econ"] == econ_filter]
    if df.empty:
        return empty_plot(t("error.no_data_period", lang))

    grouped = (
        df.groupby(["func_sub", "year"], as_index=False)["per_capita_real_expenditure"]
        .sum()
        .sort_values("year")
        .rename(columns={"per_capita_real_expenditure": "value"})
    )

    currency_code = None
    if basic_country_data:
        info = server_store.get("basic_country_info").get(country, {})
        currency_code = info.get("currency_code")

    # Fixed display order; skip levels this country/filter doesn't report.
    present = set(grouped["func_sub"].unique())
    ordered = [f for f in config.func_sub_order if f in present]

    fig = go.Figure()
    for func_sub in ordered:
        # Drop 0/missing values — they mean unreported spending (or no
        # population), not a real zero, so the line skips those years.
        sub = grouped[
            (grouped["func_sub"] == func_sub)
            & grouped["value"].notna()
            & (grouped["value"] != 0)
        ]
        if sub.empty:
            continue
        level = config.func_sub_to_level[func_sub]
        label = t(f"level.{level}", lang)
        color = config.level_colors.get(level)
        if currency_code:
            formatted = sub["value"].apply(
                lambda v: format_currency(v, currency_code, lang=lang)
            )
            customdata = np.column_stack([formatted])
            hovertemplate = f"<b>{label}</b>: %{{customdata[0]}}<extra></extra>"
        else:
            customdata = None
            hovertemplate = f"<b>{label}</b>: %{{y}}<extra></extra>"
        fig.add_trace(
            go.Scatter(
                name=label,
                x=sub["year"],
                y=sub["value"],
                mode="lines+markers",
                line=dict(color=color),
                marker=dict(color=color),
                customdata=customdata,
                hovertemplate=hovertemplate,
            )
        )

    _apply_shared_xaxis(config, fig, country, econ_filter)
    fig.update_yaxes(fixedrange=True)
    return _finalize(fig, t(config.chart_title_key, lang), lang)


def spending_narrative(config, country, econ_filter, lang="en"):
    """Which level got the most/least per-capita spending, with the averages."""
    lang = lang or "en"
    if not country:
        return t("loading", lang)

    df = server_store.get(config.store_key)
    df = df[
        (df["country_name"] == country)
        & (df["func_sub"].isin(config.func_sub_order))
        & df["per_capita_real_expenditure"].notna()
        & (df["per_capita_real_expenditure"] != 0)
    ]
    if econ_filter and econ_filter != ALL_ECON:
        df = df[df["econ"] == econ_filter]
    if df.empty:
        return t("error.no_data_period", lang)

    currency_code = (
        server_store.get("basic_country_info").get(country, {}).get("currency_code")
    )

    def _fmt(value):
        if currency_code:
            return format_currency(value, currency_code, lang=lang)
        return millify(value, lang=lang)

    # Make the selected economic category explicit (lowercased for mid-sentence).
    if econ_filter and econ_filter != ALL_ECON:
        scope = t(
            "narrative.econ_scope_one", lang,
            econ=translate_econ(econ_filter, lang).lower(),
        )
    else:
        scope = t("narrative.econ_scope_all", lang)

    # Rank levels by average yearly per-capita spending. Sum across econ
    # categories to the per-year total first (matching the chart), then average
    # over years — so the figures match the chart and a level with more years of
    # data isn't favored over one with fewer.
    totals = df.groupby(["func_sub", "year"], as_index=False)[
        "per_capita_real_expenditure"
    ].sum()
    means = totals.groupby("func_sub")["per_capita_real_expenditure"].mean()
    start_year, end_year = int(totals["year"].min()), int(totals["year"].max())
    most_key = means.idxmax()
    most_label = t(f"level.{config.func_sub_to_level[most_key]}.long", lang)

    if len(means) == 1:
        return t(
            "narrative.func_sub_single", lang,
            scope=scope, level=most_label, start=start_year, end=end_year,
            level_val=_fmt(means.loc[most_key]),
        )
    least_key = means.idxmin()
    least_label = t(f"level.{config.func_sub_to_level[least_key]}.long", lang)
    return t(
        "narrative.func_sub_most_least", lang,
        scope=scope, most=most_label, least=least_label,
        start=start_year, end=end_year,
        most_val=_fmt(means.loc[most_key]), least_val=_fmt(means.loc[least_key]),
    )


def outcome_figure(config, country, econ_filter, indicator, lang="en"):
    """Service-delivery indicator by level; shares the spending chart's x-axis."""
    lang = lang or "en"
    if not country:
        return empty_plot(t("loading", lang))

    cfg = config.outcome_by_key.get(indicator) or config.outcome_by_key[
        config.default_outcome_key
    ]
    df = server_store.get(cfg["store_key"])
    df = df[df["country_name"] == country].sort_values("year")

    fig = go.Figure()
    for level in config.level_order:
        col = cfg["columns"].get(level)
        if not col or col not in df.columns:
            continue
        # Drop missing and 0 values (0 = not reported, not a real zero).
        series = df[["year", col]].dropna()
        series = series[series[col] != 0]
        if series.empty:
            continue
        label = t(f"level.{level}", lang)
        color = config.level_colors.get(level)
        fig.add_trace(
            go.Scatter(
                name=label,
                x=series["year"],
                y=series[col],
                mode="lines+markers",
                line=dict(color=color),
                marker=dict(color=color),
                hovertemplate=f"<b>{label}</b>: %{{y:{cfg['value_fmt']}}}{cfg['suffix']}<extra></extra>",
            )
        )

    if not fig.data:
        return empty_plot(t("error.no_data_period", lang))

    _apply_shared_xaxis(config, fig, country, econ_filter)
    fig.update_yaxes(fixedrange=True, title_text=t(cfg["axis_key"], lang))
    if cfg["y_range"]:
        fig.update_yaxes(range=cfg["y_range"])
    return _finalize(fig, t(cfg["title_key"], lang), lang)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def layout(config, lang="en"):
    """The full section: divider, heading, filter bar, both charts, narrative."""
    lang = lang or "en"
    outcome_options = [
        {"label": t(label_key, lang), "value": value}
        for value, label_key in config.outcome_options
    ]
    return html.Div(
        [
            dbc.Row(dbc.Col(html.Hr())),
            dbc.Row(dbc.Col(html.H3(children=t(config.heading_key, lang)))),
            econ_outcome_filter.filter_bar(
                config.econ_filter_id,
                config.outcome_filter_id,
                outcome_options,
                lang,
                outcome_value=config.default_outcome_key,
            ),
            # Spending and outcome charts side by side.
            dbc.Row(
                [
                    dbc.Col(chart_container(config.spending_chart_id), xs=12, lg=6),
                    dbc.Col(chart_container(config.outcome_chart_id), xs=12, lg=6),
                ]
            ),
            # Narrative below the charts.
            dbc.Row(
                dbc.Col(html.P(id=config.narrative_id, children=t("loading", lang)))
            ),
        ]
    )


# ===========================================================================
# Education instance
# ===========================================================================
# Canonical education levels — both charts label and color their legend entries
# from this single model. Colors come from the QUALITATIVE palette (ColorBrewer
# Paired): blue family for primary-and-earlier, green for secondary, orange for
# post-secondary/tertiary. Levels that never share a chart may reuse a shade.
_EDU_LEVEL_ORDER = (
    "pre_primary", "primary", "primary_secondary", "lower_secondary",
    "secondary", "upper_secondary", "post_secondary", "tertiary",
)
_EDU_LEVEL_COLORS = {
    "pre_primary":       QUALITATIVE[0],  # light blue
    "primary":           QUALITATIVE[1],  # blue
    "primary_secondary": QUALITATIVE[2],  # light green
    "lower_secondary":   QUALITATIVE[2],  # light green
    "secondary":         QUALITATIVE[3],  # green
    "upper_secondary":   QUALITATIVE[3],  # green
    "post_secondary":    QUALITATIVE[6],  # light orange
    "tertiary":          QUALITATIVE[7],  # orange
}
_EDU_FUNC_SUB_TO_LEVEL = {
    "Primary Education": "primary",
    "Primary and Secondary education": "primary_secondary",
    "Secondary Education": "secondary",
    "Post-Secondary Non-Tertiary Education": "post_secondary",
    "Tertiary Education": "tertiary",
}

_TEACHER_SALARY_OUTCOME = {
    "store_key": "teacher_salaries",
    "title_key": "chart.teacher_salary",
    "axis_key": "axis.teacher_salary",
    "value_fmt": ".2f",
    "suffix": "",
    "y_range": None,
    "columns": {
        "pre_primary": "teacher_salary_pre_primary",
        "primary": "teacher_salary_primary",
        "lower_secondary": "teacher_salary_lower_secondary",
        "upper_secondary": "teacher_salary_upper_secondary",
    },
}
_ELECTRICITY_OUTCOME = {
    "store_key": "school_basic_services",
    "title_key": "chart.schools_electricity",
    "axis_key": "axis.pct_schools",
    "value_fmt": ".1f",
    "suffix": "%",
    "y_range": [0, 100],
    "columns": {
        "primary": "schools_with_electricity_primary",
        "lower_secondary": "schools_with_electricity_lower_secondary",
        "upper_secondary": "schools_with_electricity_upper_secondary",
    },
}
_INTERNET_OUTCOME = {
    "store_key": "school_basic_services",
    "title_key": "chart.schools_internet",
    "axis_key": "axis.pct_schools",
    "value_fmt": ".1f",
    "suffix": "%",
    "y_range": [0, 100],
    "columns": {
        "primary": "schools_with_internet_primary",
        "lower_secondary": "schools_with_internet_lower_secondary",
        "upper_secondary": "schools_with_internet_upper_secondary",
    },
}
_COMPLETION_RATE_OUTCOME = {
    "store_key": "completion_rates",
    "title_key": "chart.completion_rate",
    "axis_key": "axis.completion_rate",
    "value_fmt": ".1f",
    "suffix": "%",
    "y_range": [0, 100],
    "columns": {
        "primary": "completion_rate_primary",
        "lower_secondary": "completion_rate_lower_secondary",
        "upper_secondary": "completion_rate_upper_secondary",
    },
}

EDU_CONFIG = SectionConfig(
    econ_filter_id="education-func-sub-econ-filter",
    outcome_filter_id="education-outcome-indicator",
    spending_chart_id="education-func-sub-econ",
    outcome_chart_id="education-level-outcome",
    narrative_id="education-func-sub-narrative",
    store_key="edu_func_sub_econ_expenditure",
    func_sub_order=(
        "Primary Education",
        "Primary and Secondary education",
        "Secondary Education",
        "Post-Secondary Non-Tertiary Education",
        "Tertiary Education",
    ),
    func_sub_to_level=_EDU_FUNC_SUB_TO_LEVEL,
    level_order=_EDU_LEVEL_ORDER,
    level_colors=_EDU_LEVEL_COLORS,
    outcome_by_key={
        "completion_rate": _COMPLETION_RATE_OUTCOME,
        "teacher_salary": _TEACHER_SALARY_OUTCOME,
        "electricity": _ELECTRICITY_OUTCOME,
        "internet": _INTERNET_OUTCOME,
    },
    outcome_options=(
        ("completion_rate", "outcome.completion_rate"),
        ("teacher_salary", "outcome.teacher_salary"),
        ("electricity", "outcome.electricity"),
        ("internet", "outcome.internet"),
    ),
    default_outcome_key="completion_rate",
    econ_default_outcome={
        "Wage bill": "teacher_salary",
        "Capital expenditures": "electricity",
        "Goods and services": "internet",
    },
    heading_key="heading.edu_func_sub_econ",
    chart_title_key="chart.edu_func_sub_econ",
)
