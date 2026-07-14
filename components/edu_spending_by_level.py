"""Education → Over Time: "Inflation-adjusted per capita public expenditure".

A spending-breakdown line chart (per-capita real education spending by level,
filterable by economic category) shown next to a service-delivery indicator
chart (completion rate / teacher salaries / schools with electricity / internet)
that the user picks independently, plus a dynamic narrative.

Following the dashboard convention, this module holds the layout builder and the
pure figure/narrative/data helpers; the ``@callback`` wrappers live in
``pages/education.py`` and delegate here.
"""
import urllib.parse

import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go
from dash import html

import server_store
from constants import START_YEAR, translate_econ
from translations import t
from utils import apply_locale, empty_plot, format_currency, millify
from viz_theme import QUALITATIVE
from components.source_metadata_popover import chart_container


# ---------------------------------------------------------------------------
# Component ids (shared between the layout here and the callbacks in the page).
# ---------------------------------------------------------------------------
ECON_FILTER_ID = "education-func-sub-econ-filter"
OUTCOME_FILTER_ID = "education-outcome-indicator"
SPENDING_CHART_ID = "education-func-sub-econ"
OUTCOME_CHART_ID = "education-level-outcome"
NARRATIVE_ID = "education-func-sub-narrative"

ALL_ECON = "__all__"


# ---------------------------------------------------------------------------
# Filter icon — inline funnel as a data URI (no icon font is loaded).
# ---------------------------------------------------------------------------
_FILTER_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' "
    "fill='#495057' viewBox='0 0 16 16'>"
    "<path d='M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334"
    "L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 "
    "3.834A.5.5 0 0 1 1.5 3.5z'/></svg>"
)
_FILTER_ICON = "data:image/svg+xml," + urllib.parse.quote(_FILTER_SVG)


# ---------------------------------------------------------------------------
# Canonical education levels — both charts label and color their legend entries
# from this single model, so a level reads identically in both legends. Order is
# pedagogical (early → late). Colors come from the QUALITATIVE palette
# (ColorBrewer Paired): blue family for primary-and-earlier, green for
# secondary, orange for post-secondary/tertiary. Levels that never share a chart
# may reuse a shade.
# ---------------------------------------------------------------------------
_LEVEL_ORDER = [
    "pre_primary",
    "primary",
    "primary_secondary",
    "lower_secondary",
    "secondary",
    "upper_secondary",
    "post_secondary",
    "tertiary",
]
_LEVEL_COLORS = {
    "pre_primary":       QUALITATIVE[0],  # light blue
    "primary":           QUALITATIVE[1],  # blue
    "primary_secondary": QUALITATIVE[2],  # light green
    "lower_secondary":   QUALITATIVE[2],  # light green
    "secondary":         QUALITATIVE[3],  # green
    "upper_secondary":   QUALITATIVE[3],  # green
    "post_secondary":    QUALITATIVE[6],  # light orange
    "tertiary":          QUALITATIVE[7],  # orange
}

# Shared legend/margin so both charts' legend boxes match in placement & style.
_LEGEND_STYLE = dict(
    orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5,
    font=dict(size=11),
)
_CHART_MARGIN = dict(l=20, r=20, t=50, b=80)

# Education sub-functions shown in the spending chart, in display order. Any
# func_sub value outside this list (nulls, mis-tagged rows) is ignored. Each maps
# to a canonical level so its legend entry matches the outcome chart.
EDU_FUNC_SUB_ORDER = [
    "Primary Education",
    "Primary and Secondary education",
    "Secondary Education",
    "Post-Secondary Non-Tertiary Education",
    "Tertiary Education",
]
_FUNC_SUB_TO_LEVEL = {
    "Primary Education": "primary",
    "Primary and Secondary education": "primary_secondary",
    "Secondary Education": "secondary",
    "Post-Secondary Non-Tertiary Education": "post_secondary",
    "Tertiary Education": "tertiary",
}

# Each economic category has a natural default service-delivery indicator.
# Selecting a category updates the indicator dropdown; the reverse is deliberately
# NOT wired, so picking a different indicator leaves the category alone.
_ECON_DEFAULT_OUTCOME = {
    "Wage bill": "teacher_salary",
    "Capital expenditures": "electricity",
    "Goods and services": "internet",
}
_DEFAULT_OUTCOME_KEY = "completion_rate"


# ---------------------------------------------------------------------------
# Service-delivery indicator configs. Each maps canonical levels to the source
# column; any indicator key not listed falls back to completion rate.
# ---------------------------------------------------------------------------
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
_OUTCOME_BY_KEY = {
    "completion_rate": _COMPLETION_RATE_OUTCOME,
    "teacher_salary": _TEACHER_SALARY_OUTCOME,
    "electricity": _ELECTRICITY_OUTCOME,
    "internet": _INTERNET_OUTCOME,
}


# ---------------------------------------------------------------------------
# Helpers
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


def _shared_year_range(country, econ_filter):
    """[min, max] year range for the x-axis, derived from the spending
    (breakdown) data only, floored at START_YEAR. Both charts use it so they
    share one x-axis — and, crucially, the outcome indicator does NOT influence
    it, so switching indicators never moves the spending chart. Returns None if
    there's no spending data.
    """
    breakdown = server_store.get("edu_func_sub_econ_expenditure")
    breakdown = breakdown[
        (breakdown["country_name"] == country)
        & (breakdown["func_sub"].isin(EDU_FUNC_SUB_ORDER))
    ]
    if econ_filter and econ_filter != ALL_ECON:
        breakdown = breakdown[breakdown["econ"] == econ_filter]

    years = breakdown["year"].tolist()
    if not years:
        return None
    years = [int(y) for y in years]
    lo, hi = max(min(years), START_YEAR), max(years)
    return (lo, hi) if lo <= hi else None


# ---------------------------------------------------------------------------
# Callback delegates (pure functions; the @callbacks live in pages/education.py)
# ---------------------------------------------------------------------------
def econ_filter_options(country, lang, current_value):
    """(options, value) for the economic-category dropdown, per country."""
    lang = lang or "en"
    options = [{"label": t("dropdown.all_econ_categories", lang), "value": ALL_ECON}]
    if country:
        df = server_store.get("edu_func_sub_econ_expenditure")
        econ_values = sorted(
            df[df["country_name"] == country]["econ"].dropna().unique()
        )
        options += [
            {"label": translate_econ(e, lang), "value": e} for e in econ_values
        ]
    valid_values = {opt["value"] for opt in options}
    value = current_value if current_value in valid_values else ALL_ECON
    return options, value


def default_outcome_indicator(econ_filter):
    """The natural service-delivery indicator for a selected economic category."""
    return _ECON_DEFAULT_OUTCOME.get(econ_filter, _DEFAULT_OUTCOME_KEY)


def spending_figure(country, econ_filter, basic_country_data, lang="en"):
    """Per-capita real education spending by level, filtered by econ category."""
    lang = lang or "en"
    if not country:
        return empty_plot(t("loading", lang))

    df = server_store.get("edu_func_sub_econ_expenditure")
    df = df[
        (df["country_name"] == country) & (df["func_sub"].isin(EDU_FUNC_SUB_ORDER))
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
    ordered = [f for f in EDU_FUNC_SUB_ORDER if f in present]

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
        level = _FUNC_SUB_TO_LEVEL[func_sub]
        label = t(f"level.{level}", lang)
        color = _LEVEL_COLORS.get(level)
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

    _apply_shared_xaxis(fig, country, econ_filter)
    fig.update_yaxes(fixedrange=True)
    return _finalize(fig, t("chart.edu_func_sub_econ", lang), lang)


def spending_narrative(country, econ_filter, lang="en"):
    """Which level got the most/least per-capita spending, with the averages."""
    lang = lang or "en"
    if not country:
        return t("loading", lang)

    df = server_store.get("edu_func_sub_econ_expenditure")
    df = df[
        (df["country_name"] == country)
        & (df["func_sub"].isin(EDU_FUNC_SUB_ORDER))
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
    most_label = t(f"level.{_FUNC_SUB_TO_LEVEL[most_key]}.long", lang)

    if len(means) == 1:
        return t(
            "narrative.edu_func_sub_single", lang,
            scope=scope, level=most_label, start=start_year, end=end_year,
            level_val=_fmt(means.loc[most_key]),
        )
    least_key = means.idxmin()
    least_label = t(f"level.{_FUNC_SUB_TO_LEVEL[least_key]}.long", lang)
    return t(
        "narrative.edu_func_sub_most_least", lang,
        scope=scope, most=most_label, least=least_label,
        start=start_year, end=end_year,
        most_val=_fmt(means.loc[most_key]), least_val=_fmt(means.loc[least_key]),
    )


def outcome_figure(country, econ_filter, indicator, lang="en"):
    """Service-delivery indicator by level; shares the spending chart's x-axis."""
    lang = lang or "en"
    if not country:
        return empty_plot(t("loading", lang))

    cfg = _OUTCOME_BY_KEY.get(indicator, _COMPLETION_RATE_OUTCOME)
    df = server_store.get(cfg["store_key"])
    df = df[df["country_name"] == country].sort_values("year")

    fig = go.Figure()
    for level in _LEVEL_ORDER:
        col = cfg["columns"].get(level)
        if not col or col not in df.columns:
            continue
        # Drop missing and 0 values (0 = not reported, not a real zero).
        series = df[["year", col]].dropna()
        series = series[series[col] != 0]
        if series.empty:
            continue
        label = t(f"level.{level}", lang)
        color = _LEVEL_COLORS.get(level)
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

    _apply_shared_xaxis(fig, country, econ_filter)
    fig.update_yaxes(fixedrange=True, title_text=t(cfg["axis_key"], lang))
    if cfg["y_range"]:
        fig.update_yaxes(range=cfg["y_range"])
    return _finalize(fig, t(cfg["title_key"], lang), lang)


def _apply_shared_xaxis(fig, country, econ_filter):
    """Apply the spending-derived shared x-axis (whole-year ticks + range)."""
    year_range = _shared_year_range(country, econ_filter)
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
# Layout
# ---------------------------------------------------------------------------
def _filter_item(label_key, select_id, value, options, lang):
    """One labeled dropdown (icon + label on top of the select)."""
    return html.Div(
        [
            html.Div(
                [
                    html.Img(src=_FILTER_ICON, className="edu-filter-icon", alt=""),
                    dbc.Label(
                        t(label_key, lang),
                        html_for=select_id,
                        className="edu-filter-label mb-0",
                    ),
                ],
                className="edu-filter-label-row",
            ),
            dbc.Select(
                id=select_id,
                size="sm",
                className="econ-filter-select",
                value=value,
                options=options,
            ),
        ],
        className="edu-filter-item",
    )


def layout(lang="en"):
    """The full section: divider, heading, filter bar, both charts, narrative."""
    lang = lang or "en"
    return html.Div(
        [
            dbc.Row(dbc.Col(html.Hr())),
            dbc.Row(
                dbc.Col(html.H3(children=t("heading.edu_func_sub_econ", lang)))
            ),
            # Both filters share one background bar, each label on top.
            html.Div(
                [
                    _filter_item(
                        "label.economic_category",
                        ECON_FILTER_ID,
                        ALL_ECON,
                        [{"label": t("dropdown.all_econ_categories", lang), "value": ALL_ECON}],
                        lang,
                    ),
                    _filter_item(
                        "label.outcome_indicator",
                        OUTCOME_FILTER_ID,
                        _DEFAULT_OUTCOME_KEY,
                        [
                            {"label": t("outcome.completion_rate", lang), "value": "completion_rate"},
                            {"label": t("outcome.teacher_salary", lang), "value": "teacher_salary"},
                            {"label": t("outcome.electricity", lang), "value": "electricity"},
                            {"label": t("outcome.internet", lang), "value": "internet"},
                        ],
                        lang,
                    ),
                ],
                className="edu-filter-bar",
            ),
            # Spending and outcome charts side by side.
            dbc.Row(
                [
                    dbc.Col(chart_container(SPENDING_CHART_ID), xs=12, lg=6),
                    dbc.Col(chart_container(OUTCOME_CHART_ID), xs=12, lg=6),
                ]
            ),
            # Narrative below the charts.
            dbc.Row(
                dbc.Col(html.P(id=NARRATIVE_ID, children=t("loading", lang)))
            ),
        ]
    )
