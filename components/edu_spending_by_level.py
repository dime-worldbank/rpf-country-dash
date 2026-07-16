"""Education spending by level, beside a service-delivery indicator.

Per-capita real spending by education level (filterable by economic category)
next to an indicator chart the user picks, plus a narrative. This module holds
the layout builder and pure helpers; the ``@callback`` wrappers live in
pages/education.py and delegate here.
"""
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import html

import server_store
from constants import START_YEAR, translate_econ
from translations import t
from utils import apply_locale, empty_plot, format_currency, millify
from viz_theme import QUALITATIVE
from trend_narrative import get_relationship_narrative
from components import econ_outcome_filter
from components.econ_outcome_filter import ALL_ECON
class SectionConfig:
from components.source_metadata_popover import chart_container

# Component ids. The two chart ids double as CHART_METADATA keys in
# components/source_metadata_popover.py — rename one and its ⓘ modal loses its
# sources.
ECON_FILTER_ID = "education-func-sub-econ-filter"
OUTCOME_FILTER_ID = "education-outcome-indicator"
SPENDING_CHART_ID = "education-func-sub-econ"
OUTCOME_CHART_ID = "education-level-outcome"
NARRATIVE_ID = "education-func-sub-narrative"

_STORE_KEY = "edu_func_sub_econ_expenditure"

# Canonical education levels — both charts label and color their legend entries
# from this single model. QUALITATIVE (ColorBrewer Paired): blue family for
# primary-and-earlier, green for secondary, orange for post-secondary/tertiary.
_LEVEL_ORDER = (
    "pre_primary", "primary", "primary_secondary",
    "secondary", "post_secondary", "tertiary",
)
_LEVEL_COLORS = {
    "pre_primary":       QUALITATIVE[0],  # light blue
    "primary":           QUALITATIVE[1],  # blue
    "primary_secondary": QUALITATIVE[2],  # light green
    "secondary":         QUALITATIVE[3],  # green
    "post_secondary":    QUALITATIVE[6],  # light orange
    "tertiary":          QUALITATIVE[7],  # orange
}
# func_sub value -> canonical level, in spending-chart display order.
_FUNC_SUB_TO_LEVEL = {
    "Primary Education": "primary",
    "Primary and Secondary education": "primary_secondary",
    "Secondary Education": "secondary",
    "Post-Secondary Non-Tertiary Education": "post_secondary",
    "Tertiary Education": "tertiary",
}

# Service-delivery indicators, in dropdown order.
_OUTCOMES = {
    "completion_rate": {
        "store_key": "completion_rates",
        "label_key": "outcome.completion_rate",
        "title_key": "chart.completion_rate",
        "metric_key": "metric.completion_rate",
        "value_fmt": ".1f",
        "suffix": "%",
        "y_range": [0, 100],
        "columns": {
            "primary": "completion_rate_primary",
            "secondary": "completion_rate_secondary",
        },
    },
    "teacher_salary": {
        "store_key": "teacher_salaries",
        "label_key": "outcome.teacher_salary",
        "title_key": "chart.teacher_salary",
        "metric_key": "metric.teacher_salary",
        "value_fmt": ".2f",
        "suffix": "",
        "y_range": None,
        "columns": {
            "pre_primary": "teacher_salary_pre_primary",
            "primary": "teacher_salary_primary",
            "secondary": "teacher_salary_secondary",
        },
    },
    "electricity": {
        "store_key": "school_basic_services",
        "label_key": "outcome.electricity",
        "title_key": "chart.schools_electricity",
        "metric_key": "metric.electricity",
        "value_fmt": ".1f",
        "suffix": "%",
        "y_range": [0, 100],
        "columns": {
            "primary": "schools_with_electricity_primary",
            "secondary": "schools_with_electricity_secondary",
        },
    },
    "internet": {
        "store_key": "school_basic_services",
        "label_key": "outcome.internet",
        "title_key": "chart.schools_internet",
        "metric_key": "metric.internet",
        "value_fmt": ".1f",
        "suffix": "%",
        "y_range": [0, 100],
        "columns": {
            "primary": "schools_with_internet_primary",
            "secondary": "schools_with_internet_secondary",
        },
    },
}
DEFAULT_OUTCOME = "completion_rate"
# Economic category -> the indicator it makes most sense to look at next to it.
_ECON_DEFAULT_OUTCOME = {
    "Wage bill": "teacher_salary",
    "Capital expenditures": "electricity",
    "Goods and services": "internet",
}

# Shared legend/margin so both charts' legend boxes match in placement & style.
_LEGEND_STYLE = dict(
    orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5,
    font=dict(size=11),
)
_CHART_MARGIN = dict(l=20, r=20, t=20, b=80)


def _year_range(years):
    """[min, max] of ``years``, floored at START_YEAR; None if empty."""
    years = [int(y) for y in years]
    if not years:
        return None
    lo, hi = max(min(years), START_YEAR), max(years)
    return (lo, hi) if lo <= hi else None


def _spending_years(country, econ_filter):
    """The spending chart's year range. The outcome indicator deliberately does
    not feed this, so switching indicators never moves either x-axis."""
    df = server_store.get(_STORE_KEY)
    df = df[
        (df["country_name"] == country)
        & (df["func_sub"].isin(list(_FUNC_SUB_TO_LEVEL)))
    ]
    if econ_filter and econ_filter != ALL_ECON:
        df = df[df["econ"] == econ_filter]
    return _year_range(df["year"])


def _apply_shared_xaxis(fig, year_range):
    """Whole-year ticks + shared range. An integer dtick stops Plotly picking a
    fractional one that ``tickformat="d"`` would round into duplicate labels."""
    fig.update_xaxes(tickformat="d")
    if year_range:
        lo, hi = year_range
        fig.update_xaxes(
            tick0=lo, dtick=max(1, round((hi - lo) / 10)), range=[lo - 0.5, hi + 0.5]
        )


def _money_fmt(currency_code, lang):
    """Formatter for spending values; falls back to millify without a currency."""
    if currency_code:
        return lambda v: format_currency(v, currency_code, lang=lang)
    return lambda v: millify(v, lang=lang)


def _currency_code(country):
    return (
        server_store.lookup("basic_country_info", {}).get(country, {}).get("currency_code")
    )


def _outcome(indicator):
    return _OUTCOMES.get(indicator) or _OUTCOMES[DEFAULT_OUTCOME]


def _finalize(fig, lang):
    """Shared layout (hover, legend, margin) + locale, common to both charts."""
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="white",
        legend=_LEGEND_STYLE,
        margin=_CHART_MARGIN,
    )
    fig.update_yaxes(automargin=True)
    return apply_locale(fig, lang)


# ---------------------------------------------------------------------------
# Callback delegates (pure functions; the @callbacks live in the page module)
# ---------------------------------------------------------------------------
def econ_filter_options(country, lang, current_value):
    """(options, value) for the economic-category dropdown, per country."""
    return econ_outcome_filter.econ_options(_STORE_KEY, country, lang, current_value)


def default_outcome_indicator(econ_filter):
    """The natural service-delivery indicator for a selected economic category."""
    return _ECON_DEFAULT_OUTCOME.get(econ_filter, DEFAULT_OUTCOME)


def spending_figure(country, econ_filter, lang="en"):
    """Per-capita real spending by level, filtered by economic category."""
    lang = lang or "en"
    if not country:
        return empty_plot(t("loading", lang))

    df = server_store.get(_STORE_KEY)
    df = df[
        (df["country_name"] == country)
        & (df["func_sub"].isin(list(_FUNC_SUB_TO_LEVEL)))
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

    currency_code = _currency_code(country)

    fig = go.Figure()
    for func_sub, level in _FUNC_SUB_TO_LEVEL.items():
        # Drop 0/missing values — they mean unreported spending (or no
        # population), not a real zero, so the line skips those years.
        sub = grouped[
            (grouped["func_sub"] == func_sub)
            & grouped["value"].notna()
            & (grouped["value"] != 0)
        ]
        if sub.empty:
            continue
        label = t(f"level.{level}", lang)
        color = _LEVEL_COLORS.get(level)
        if currency_code:
            customdata = sub["value"].apply(_money_fmt(currency_code, lang))
            hovertemplate = f"<b>{label}</b>: %{{customdata}}<extra></extra>"
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

    _apply_shared_xaxis(fig, _year_range(grouped["year"]))
    if econ_filter and econ_filter != ALL_ECON:
        scope = translate_econ(econ_filter, lang)
    else:
        scope = t("dropdown.all_econ_categories", lang)
    fig.update_yaxes(
        fixedrange=True,
        title_text=f"{t('chart.edu_func_sub_econ', lang)}<br>({scope})",
    )
    return _finalize(fig, lang)


def _relationship_sentence(
    country, econ_filter, indicator, most_key, totals, currency_code, lang,
):
    """Detected relationship between the best-funded level's spending and the
    selected indicator for that same level. "" when the level isn't in the
    indicator or there's too little overlapping data."""
    cfg = _outcome(indicator)
    level = _FUNC_SUB_TO_LEVEL[most_key]
    col = cfg["columns"].get(level)
    if not col:
        return ""

    spend = totals[totals["func_sub"] == most_key].sort_values("year")
    outcome = server_store.get(cfg["store_key"])
    outcome = outcome[outcome["country_name"] == country][["year", col]].dropna()
    outcome = outcome[outcome[col] != 0]
    # Restrict the outcome to the shared x-axis window.
    year_range = _spending_years(country, econ_filter)
    if year_range:
        lo, hi = year_range
        outcome = outcome[(outcome["year"] >= lo) & (outcome["year"] <= hi)]
    outcome = outcome.sort_values("year")
    if len(spend) < 2 or len(outcome) < 2:
        return ""

    result = get_relationship_narrative(
        reference_years=spend["year"].values,
        reference_values=spend["per_capita_real_expenditure"].values,
        comparison_years=outcome["year"].values,
        comparison_values=outcome[col].values,
        reference_name=t(
            "metric.level_spending", lang, level=t(f"level.{level}.long", lang)
        ),
        comparison_name=t(
            "metric.level_outcome", lang,
            level=t(f"level.{level}", lang).lower(),
            indicator=t(cfg["metric_key"], lang),
        ),
        reference_format=_money_fmt(currency_code, lang),
        comparison_format=cfg["value_fmt"],
        lang=lang,
    )
    if result.get("method") == "insufficient_data":
        return ""
    return result.get("narrative", "")


def spending_narrative(country, econ_filter, indicator, lang="en"):
    """Most/least funded level with averages, plus the detected relationship
    between the best-funded level's spending and the selected indicator (when
    that level is reported by the indicator)."""
    lang = lang or "en"
    if not country:
        return t("loading", lang)

    df = server_store.get(_STORE_KEY)
    df = df[
        (df["country_name"] == country)
        & (df["func_sub"].isin(list(_FUNC_SUB_TO_LEVEL)))
        & df["per_capita_real_expenditure"].notna()
        & (df["per_capita_real_expenditure"] != 0)
    ]
    if econ_filter and econ_filter != ALL_ECON:
        df = df[df["econ"] == econ_filter]
    if df.empty:
        return t("error.no_data_period", lang)

    currency_code = _currency_code(country)
    _fmt = _money_fmt(currency_code, lang)

    if econ_filter and econ_filter != ALL_ECON:
        scope = t(
            "narrative.econ_scope_one", lang,
            econ=translate_econ(econ_filter, lang).lower(),
        )
    else:
        scope = t("narrative.econ_scope_all", lang)

    # Sum across econ categories to the per-year total before averaging, so the
    # figures match the chart and a level with more years isn't favored.
    totals = df.groupby(["func_sub", "year"], as_index=False)[
        "per_capita_real_expenditure"
    ].sum()
    means = totals.groupby("func_sub")["per_capita_real_expenditure"].mean()
    start_year, end_year = int(totals["year"].min()), int(totals["year"].max())
    most_key = means.idxmax()
    most_label = t(f"level.{_FUNC_SUB_TO_LEVEL[most_key]}.long", lang)

    if len(means) == 1:
        base = t(
            "narrative.func_sub_single", lang,
            scope=scope, level=most_label, start=start_year, end=end_year,
            level_val=_fmt(means.loc[most_key]),
        )
    else:
        least_key = means.idxmin()
        least_label = t(f"level.{_FUNC_SUB_TO_LEVEL[least_key]}.long", lang)
        base = t(
            "narrative.func_sub_most_least", lang,
            scope=scope, most=most_label, least=least_label,
            start=start_year, end=end_year,
            most_val=_fmt(means.loc[most_key]), least_val=_fmt(means.loc[least_key]),
        )

    relationship = _relationship_sentence(
        country, econ_filter, indicator, most_key, totals, currency_code, lang,
    )
    return " ".join(p for p in (base, relationship) if p)


def outcome_figure(country, econ_filter, indicator, lang="en"):
    """Service-delivery indicator by level; shares the spending chart's x-axis."""
    lang = lang or "en"
    if not country:
        return empty_plot(t("loading", lang))

    cfg = _outcome(indicator)
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

    _apply_shared_xaxis(fig, _spending_years(country, econ_filter))
    fig.update_yaxes(fixedrange=True, title_text=t(cfg["title_key"], lang))
    if cfg["y_range"]:
        fig.update_yaxes(range=cfg["y_range"])
    return _finalize(fig, lang)


def layout(lang="en"):
    """The full section: divider, heading, filter bar, both charts, narrative."""
    lang = lang or "en"
    outcome_options = [
        {"label": t(cfg["label_key"], lang), "value": key}
        for key, cfg in _OUTCOMES.items()
    ]
    return html.Div(
        [
            dbc.Row(dbc.Col(html.Hr())),
            dbc.Row(dbc.Col(html.H3(children=t("heading.edu_func_sub_econ", lang)))),
            econ_outcome_filter.filter_bar(
                ECON_FILTER_ID, OUTCOME_FILTER_ID, outcome_options, DEFAULT_OUTCOME, lang,
            ),
            dbc.Row(dbc.Col(html.P(id=NARRATIVE_ID, children=t("loading", lang)))),
            dbc.Row(
                [
                    dbc.Col(chart_container(SPENDING_CHART_ID), xs=12, lg=6),
                    dbc.Col(chart_container(OUTCOME_CHART_ID), xs=12, lg=6),
                ]
            ),
        ]
    )
