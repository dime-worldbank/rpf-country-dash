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
from constants import (
    EDU_OUTCOME_CHART_ID as OUTCOME_CHART_ID,
    EDU_SPENDING_CHART_ID as SPENDING_CHART_ID,
    translate_econ,
)
from translations import t
from utils import (
    apply_locale,
    empty_plot,
    filter_country_sort_year,
    format_currency,
    get_currency_code,
)
from viz_theme import QUALITATIVE
from trend_narrative import get_relationship_narrative
from components import econ_outcome_filter
from components.econ_outcome_filter import ALL_ECON
from components.source_metadata_popover import chart_container

# Component ids. The two chart ids come from constants.py because they double as
# CHART_METADATA keys; the rest are local. All are re-exported here so the page
# has one place to import section ids from.
ECON_FILTER_ID = "education-func-sub-econ-filter"
OUTCOME_FILTER_ID = "education-outcome-indicator"
NARRATIVE_ID = "education-func-sub-narrative"

_STORE_KEY = "edu_func_sub_econ_expenditure"

# Levels in display order (both charts follow it), each with its line colour and
# the BOOST func_sub it maps to — None where spending has no matching category
# (pre-primary). Colours skip the red pair QUALITATIVE[4:6] so the primary,
# secondary and tertiary families stay visually distinct.
EDUCATION_LEVELS = {
    "pre_primary":       {"color": QUALITATIVE[0], "func_sub": None},
    "primary":           {"color": QUALITATIVE[1], "func_sub": "Primary Education"},
    "primary_secondary": {"color": QUALITATIVE[2], "func_sub": "Primary and Secondary education"},
    "secondary":         {"color": QUALITATIVE[3], "func_sub": "Secondary Education"},
    "post_secondary":    {"color": QUALITATIVE[6], "func_sub": "Post-Secondary Non-Tertiary Education"},
    "tertiary":          {"color": QUALITATIVE[7], "func_sub": "Tertiary Education"},
}
# Reverse view for the spending chart, which groups rows by ``func_sub``: maps
# func_sub -> level in the same order, skipping levels with no spending category.
_LEVEL_BY_FUNC_SUB = {
    m["func_sub"]: level for level, m in EDUCATION_LEVELS.items() if m["func_sub"]
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


def select_spending_rows(country, econ_filter):
    df = filter_country_sort_year(server_store.get(_STORE_KEY), country)
    df = df[df["func_sub"].isin(list(_LEVEL_BY_FUNC_SUB))]
    if econ_filter and econ_filter != ALL_ECON:
        df = df[df["econ"] == econ_filter]
    return df


def drop_unreported_years(df, value_col):
    # 0 and NaN both mean "not reported", never a real zero.
    return df[df[value_col].notna() & (df[value_col] != 0)]


def sum_reported_level_totals(df):
    # Sum before dropping unreported, so years whose categories net to zero drop out.
    totals = (
        df.groupby(["func_sub", "year"], as_index=False)["per_capita_real_expenditure"]
        .sum()
        .rename(columns={"per_capita_real_expenditure": "value"})
        .sort_values("year")
    )
    return drop_unreported_years(totals, "value")


def find_year_bounds(years):
    years = [int(y) for y in years]
    return (min(years), max(years)) if years else None


def apply_shared_xaxis(fig, year_bounds):
    # Integer dtick: a fractional one rounds to duplicate labels under tickformat="d".
    fig.update_xaxes(tickformat="d")
    if year_bounds:
        lo, hi = year_bounds
        fig.update_xaxes(
            tick0=lo, dtick=max(1, round((hi - lo) / 10)), range=[lo - 0.5, hi + 0.5]
        )


def resolve_outcome_config(indicator):
    return _OUTCOMES.get(indicator) or _OUTCOMES[DEFAULT_OUTCOME]


def apply_shared_layout(fig, lang):
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="white",
        legend=_LEGEND_STYLE,
    )
    fig.update_yaxes(automargin=True)
    return apply_locale(fig, lang)


# ---------------------------------------------------------------------------
# Callback delegates (pure functions; the @callbacks live in the page module)
# ---------------------------------------------------------------------------
def get_econ_category_options(country, lang, current_value):
    """(options, value) for the economic-category dropdown, per country."""
    options = [{"label": t("dropdown.all_econ_categories", lang), "value": ALL_ECON}]
    if country:
        df = server_store.get(_STORE_KEY)
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
    return _ECON_DEFAULT_OUTCOME.get(econ_filter, DEFAULT_OUTCOME)


def spending_figure(country, econ_filter, lang="en"):
    """Per-capita real spending by level, filtered by economic category."""
    if not country:
        return empty_plot(t("loading", lang))

    totals = sum_reported_level_totals(select_spending_rows(country, econ_filter))
    if totals.empty:
        return empty_plot(t("error.no_data_period", lang))

    currency_code = get_currency_code(country)
    format_spend = lambda x: format_currency(x, currency_code, lang=lang)

    fig = go.Figure()
    for func_sub, level in _LEVEL_BY_FUNC_SUB.items():
        sub = totals[totals["func_sub"] == func_sub]
        if sub.empty:
            continue
        label = t(f"level.{level}", lang)
        color = EDUCATION_LEVELS[level]["color"]
        fig.add_trace(
            go.Scatter(
                name=label,
                x=sub["year"],
                y=sub["value"],
                mode="lines+markers",
                line=dict(color=color),
                marker=dict(color=color),
                customdata=sub["value"].apply(format_spend),
                hovertemplate=f"<b>{label}</b>: %{{customdata}}<extra></extra>",
            )
        )

    apply_shared_xaxis(fig, find_year_bounds(totals["year"]))
    if econ_filter and econ_filter != ALL_ECON:
        scope = translate_econ(econ_filter, lang)
    else:
        scope = t("dropdown.all_econ_categories", lang)
    fig.update_yaxes(
        fixedrange=True,
        title_text=f"{t('chart.edu_func_sub_econ', lang)}<br>({scope})",
    )
    return apply_shared_layout(fig, lang)


def build_relationship_sentence(
    country, indicator, most_key, totals, currency_code, lang,
):
    cfg = resolve_outcome_config(indicator)
    level = _LEVEL_BY_FUNC_SUB[most_key]
    col = cfg["columns"].get(level)
    if not col:
        return ""

    spend = totals[totals["func_sub"] == most_key].sort_values("year")
    outcome = server_store.get(cfg["store_key"])
    if col not in outcome.columns:
        return ""
    outcome = drop_unreported_years(
        filter_country_sort_year(outcome, country)[["year", col]], col
    )
    year_bounds = find_year_bounds(totals["year"])
    if year_bounds:
        lo, hi = year_bounds
        outcome = outcome[(outcome["year"] >= lo) & (outcome["year"] <= hi)]
    outcome = outcome.sort_values("year")
    if len(spend) < 2 or len(outcome) < 2:
        return ""

    result = get_relationship_narrative(
        reference_years=spend["year"].values,
        reference_values=spend["value"].values,
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
        reference_format=lambda x: format_currency(x, currency_code, lang=lang),
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
    if not country:
        return t("loading", lang)

    totals = sum_reported_level_totals(select_spending_rows(country, econ_filter))
    if totals.empty:
        return t("error.no_data_period", lang)

    currency_code = get_currency_code(country)
    format_spend = lambda x: format_currency(x, currency_code, lang=lang)

    if econ_filter and econ_filter != ALL_ECON:
        scope = t(
            "narrative.econ_scope_one", lang,
            econ=translate_econ(econ_filter, lang).lower(),
        )
    else:
        scope = t("narrative.econ_scope_all", lang)

    # Averaged over the same per-year totals the chart plots, so the figures
    # agree with it and a level with more reported years isn't favored.
    means = totals.groupby("func_sub")["value"].mean()
    start_year, end_year = int(totals["year"].min()), int(totals["year"].max())
    most_key = means.idxmax()
    most_label = t(f"level.{_LEVEL_BY_FUNC_SUB[most_key]}.long", lang)

    if len(means) == 1:
        base = t(
            "narrative.func_sub_single", lang,
            scope=scope, level=most_label, start=start_year, end=end_year,
            level_val=format_spend(means.loc[most_key]),
        )
    else:
        least_key = means.idxmin()
        least_label = t(f"level.{_LEVEL_BY_FUNC_SUB[least_key]}.long", lang)
        base = t(
            "narrative.func_sub_most_least", lang,
            scope=scope, most=most_label, least=least_label,
            start=start_year, end=end_year,
            most_val=format_spend(means.loc[most_key]), least_val=format_spend(means.loc[least_key]),
        )

    relationship = build_relationship_sentence(
        country, indicator, most_key, totals, currency_code, lang,
    )
    return " ".join(p for p in (base, relationship) if p)


def outcome_figure(country, econ_filter, indicator, lang="en"):
    """Service-delivery indicator by level.

    Shares the spending chart's x-axis so the pair reads as one view, but stands
    on its own: when the economic filter leaves no spending to plot, this chart
    still renders over its own years.
    """
    if not country:
        return empty_plot(t("loading", lang))

    cfg = resolve_outcome_config(indicator)
    df = filter_country_sort_year(server_store.get(cfg["store_key"]), country)
    df = df.sort_values("year")

    fig = go.Figure()
    plotted_years = []
    for level in EDUCATION_LEVELS:
        col = cfg["columns"].get(level)
        if not col or col not in df.columns:
            continue
        series = drop_unreported_years(df[["year", col]], col)
        if series.empty:
            continue
        plotted_years.extend(series["year"])
        label = t(f"level.{level}", lang)
        color = EDUCATION_LEVELS[level]["color"]
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

    # Align to the spending chart's years (computed from spending alone, so the
    # indicator never moves the axis); fall back to this chart's own years when
    # the econ filter leaves no spending to align to.
    spending_bounds = find_year_bounds(
        sum_reported_level_totals(select_spending_rows(country, econ_filter))["year"]
    )
    apply_shared_xaxis(fig, spending_bounds or find_year_bounds(plotted_years))
    fig.update_yaxes(fixedrange=True, title_text=t(cfg["title_key"], lang))
    if cfg["y_range"]:
        fig.update_yaxes(range=cfg["y_range"])
    return apply_shared_layout(fig, lang)


def layout(lang="en"):
    """The full section: divider, heading, filter bar, both charts, narrative."""
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
