import numpy as np
import plotly.graph_objects as go

from translations import t, genitive
from trend_narrative import InsightExtractor, TrendDetector
from trend_narrative_i18n import get_segment_narrative_i18n
from utils import (
    apply_locale,
    empty_plot,
    filter_country_sort_year,
    format_currency,
)
import server_store

# Kept off blue: total_figure above uses the central-government blue.
DOMESTIC_FUNDED_COLOR = "#8E6BA6"
FOREIGN_FUNDED_COLOR = "#E0AE3C"
TOTAL_BUDGET_COLOR = "#3A3F47"

EXECUTED_COLOR = "#2E8B6B"  # budget spent
SHORTFALL_COLOR = "#C0503A"  # budget unspent
REFERENCE_LINE_COLOR = "#8A8F98"


def _prepare_funding_df(country):
    """Per-year total budget for ``country``, with the domestic/foreign split.

    Keeps every year that has a budget so the total-budget line shows even when
    the funding breakdown is missing; the split columns are NaN for years (or
    countries) that don't report ``foreign_funded_budget``, rather than implying
    an all-domestic split.

    Deliberately budget-based, not expenditure-based: foreign-sourced execution
    is not tracked for Togo, which would render the split as flat 100% domestic.
    """
    df = server_store.get("expenditure_w_poverty")
    df = filter_country_sort_year(df, country)
    if df.empty or "budget" not in df.columns:
        return df.iloc[0:0]

    df = df.copy()
    df = df[df["budget"].notna() & (df["budget"].round(0) != 0)]
    if df.empty:
        return df

    if "foreign_funded_budget" not in df.columns:
        df["foreign_funded_budget"] = np.nan
    df["domestic_funded_budget"] = df["budget"] - df["foreign_funded_budget"]
    df["domestic_share"] = df["domestic_funded_budget"] / df["budget"] * 100
    df["foreign_share"] = df["foreign_funded_budget"] / df["budget"] * 100

    # Deflate every amount by the same factor, so the real bars still sum to the
    # real total and the shares are unchanged.
    deflator = _deflator(df)
    df["real_budget"] = df["budget"] * deflator
    df["real_domestic_funded_budget"] = df["domestic_funded_budget"] * deflator
    df["real_foreign_funded_budget"] = df["foreign_funded_budget"] * deflator
    return df.sort_values("year")


def _deflator(df):
    """``real_expenditure / expenditure``; NaN where unavailable or expenditure is zero."""
    if not {"expenditure", "real_expenditure"}.issubset(df.columns):
        return np.nan
    expenditure = df["expenditure"].where(df["expenditure"] != 0)
    return df["real_expenditure"] / expenditure


def render_funding(country, lang="en", budget_terms="nominal"):
    """Funding figure and its narrative, from one shared data prep.

    Returned together so a single callback updates the chart and its text in one
    round-trip, keeping the narrative from lagging the chart on a toggle.
    """
    funding_df = _prepare_funding_df(country)
    if funding_df.empty:
        unavailable = t("error.data_unavailable", lang)
        return empty_plot(unavailable), unavailable
    currency_code = server_store.get("basic_country_info")[country]["currency_code"]
    fig = create_funding_source_figure(funding_df, currency_code, lang=lang, budget_terms=budget_terms)
    narrative = format_funding_source_narrative(funding_df, country, lang=lang, budget_terms=budget_terms)
    return fig, narrative


def render_execution_narrative(country, lang="en"):
    execution_df = _prepare_execution_df(country)
    if execution_df.empty:
        return t("error.data_unavailable", lang)
    return format_execution_narrative(execution_df, country, lang=lang)


def create_funding_source_figure(df, currency_code, lang="en", budget_terms="nominal"):
    """Total-budget line, plus the domestic/foreign split where it's available.

    Countries that report only a total (no ``foreign_funded_budget``) get a plain
    total-budget line rather than an empty funding chart.
    """
    real = budget_terms == "real"
    has_split = df["domestic_share"].notna().any()

    def as_currency(values):
        return values.apply(lambda x: format_currency(x, currency_code, lang=lang))

    fig = go.Figure()

    if has_split:
        bars = [
            ("domestic_funded_budget", "real_domestic_funded_budget", "domestic_share",
             t("trace.domestic_funded", lang), DOMESTIC_FUNDED_COLOR),
            ("foreign_funded_budget", "real_foreign_funded_budget", "foreign_share",
             t("trace.foreign_funded", lang), FOREIGN_FUNDED_COLOR),
        ]
        for nominal_col, real_col, share_col, name, color in bars:
            share = df[share_col]
            amounts = as_currency(df[real_col if real else nominal_col])
            fig.add_trace(
                go.Bar(
                    name=name,
                    x=df["year"],
                    y=share,
                    marker_color=color,
                    customdata=np.column_stack([amounts, share]),
                    hovertemplate=(
                        "<b>" + name + "</b>: "
                        "%{customdata[1]:.1f}% (%{customdata[0]})<extra></extra>"
                    ),
                )
            )

    total_col = "real_budget" if real else "budget"
    # Constant, compact legend label; the radio conveys nominal vs inflation-
    # adjusted, and a longer label wraps the legend into the title.
    total_name = t("trace.total_budget", lang)
    fig.add_trace(
        go.Scatter(
            name=total_name,
            x=df["year"],
            y=df[total_col],
            yaxis="y2" if has_split else "y",
            mode="lines+markers",
            marker_color=TOTAL_BUDGET_COLOR,
            customdata=np.column_stack([as_currency(df[total_col])]),
            hovertemplate="<b>" + total_name + "</b>: %{customdata[0]}<extra></extra>",
        )
    )

    fig.update_xaxes(tickformat="d")
    if has_split:
        # Bars carry the share on the left axis; the total line on the right.
        fig.update_yaxes(
            title_text=t("axis.budget_share", lang),
            ticksuffix="%",
            range=[0, 100],
            fixedrange=True,
        )
        fig.update_layout(
            barmode="stack",
            title=t("chart.budget_by_funding_source", lang),
            yaxis2=dict(
                title_text=total_name,
                overlaying="y",
                side="right",
                showgrid=False,
                rangemode="tozero",
                fixedrange=True,
            ),
        )
    else:
        # No breakdown: just the total budget on a single axis.
        fig.update_yaxes(title_text=total_name, rangemode="tozero", fixedrange=True)
        fig.update_layout(title=t("chart.total_budget_over_time", lang), showlegend=False)

    fig.update_layout(
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
        hovermode="x unified",
    )
    return apply_locale(fig, lang)


def format_funding_source_narrative(df, country, lang="en", budget_terms="nominal"):
    country_label = t(f"country.{country}", lang)

    # Total-budget trend, for the terms currently shown.
    real = budget_terms == "real"
    total_col = "real_budget" if real else "budget"
    metric_key = "metric.total_budget_real" if real else "metric.total_budget"
    budget_df = df.dropna(subset=[total_col]).sort_values("year")
    trend = ""
    if len(budget_df) >= 2:
        extractor = InsightExtractor(
            budget_df["year"].values,
            budget_df[total_col].values,
            detector=TrendDetector(),
        )
        trend = get_segment_narrative_i18n(
            extractor=extractor,
            metric=t(metric_key, lang),
            lang=lang,
        )
        if trend:
            trend = trend[0].upper() + trend[1:]

    # The funding split where the breakdown exists; otherwise say it's unknown
    # rather than drop it silently (silence would read as "no foreign funding").
    # The trend already covers the total.
    shares = df["domestic_share"].dropna()
    if not shares.empty:
        average = t(
            "narrative.funding_source_average",
            lang,
            country=country_label,
            country_gen=genitive(lang, country_label),
            domestic_share=shares.mean(),
            foreign_share=100 - shares.mean(),
        )
    elif len(df):
        average = t("narrative.funding_source_unavailable", lang)
    else:
        average = ""

    parts = [p for p in (trend, average) if p]
    return " ".join(parts) if parts else t("error.data_unavailable", lang)


def _prepare_execution_df(country):
    """Per-year budget execution for ``country`` (expenditure vs budget).

    Filters on expenditure, not the foreign-funding split, so it keeps years the
    funding chart drops.
    """
    df = server_store.get("expenditure_w_poverty")
    df = filter_country_sort_year(df, country)
    if df.empty or "budget" not in df.columns or "expenditure" not in df.columns:
        return df.iloc[0:0]

    df = df.copy()
    df = df[
        df["budget"].notna()
        & (df["budget"].round(0) != 0)
        & df["expenditure"].notna()
    ]
    if df.empty:
        return df

    df["execution_rate"] = df["expenditure"] / df["budget"] * 100
    df["execution_variance"] = df["execution_rate"] - 100
    return df.sort_values("year")


def render_execution_figure(country, lang="en", metric="execution_rate"):
    execution_df = _prepare_execution_df(country)
    if execution_df.empty:
        return empty_plot(t("error.data_unavailable", lang))
    return create_execution_figure(execution_df, lang=lang, metric=metric)


def create_execution_figure(df, lang="en", metric="execution_rate"):
    """``metric`` selects the ``execution_rate`` or its ``variance`` from budget."""
    variance = metric == "variance"

    if variance:
        col, reference, axis = "execution_variance", 0, t("axis.execution_variance", lang)
        color = [EXECUTED_COLOR if v >= 0 else SHORTFALL_COLOR for v in df[col]]
    else:
        col, reference, axis = "execution_rate", 100, t("axis.execution_rate", lang)
        color = EXECUTED_COLOR

    fig = go.Figure(
        go.Bar(
            x=df["year"],
            y=df[col],
            marker_color=color,
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_hline(y=reference, line_dash="dash", line_color=REFERENCE_LINE_COLOR)
    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(title_text=axis, ticksuffix="%", fixedrange=True)
    fig.update_layout(
        title=t("chart.budget_execution", lang),
        plot_bgcolor="white",
        showlegend=False,
        hovermode="x unified",
    )
    return apply_locale(fig, lang)


# PEFA PI-1 rates a budget credible when execution stays within ±3% of the
# approved budget; outside that band is under- or over-execution.
CREDIBLE_BAND = (97, 103)
# Recent moves smaller than this read as flat rather than a rise or fall.
STEADY_MARGIN = 2


def format_execution_narrative(df, country, lang="en"):
    country_label = t(f"country.{country}", lang)
    plot_df = df.dropna(subset=["execution_rate"]).sort_values("year")
    mean_rate = plot_df["execution_rate"].mean()

    low, high = CREDIBLE_BAND
    if mean_rate < low:
        key, gap = "narrative.execution_under", 100 - mean_rate
    elif mean_rate > high:
        key, gap = "narrative.execution_over", mean_rate - 100
    else:
        key, gap = "narrative.execution_on_track", 0
    # No period phrase: the funding paragraph above already states the years.
    lead = t(key, lang, country=country_label, mean=mean_rate, gap=gap)
    lead = lead[0].upper() + lead[1:]

    recent = plot_df.tail(5)
    if len(recent) < 2:
        return lead

    first = recent["execution_rate"].iloc[0]
    last = recent["execution_rate"].iloc[-1]
    n = len(recent)
    if abs(last - first) < STEADY_MARGIN:
        recent_text = t("narrative.execution_recent_steady", lang, n=n, latest=last)
    elif last > first:
        recent_text = t("narrative.execution_recent_rose", lang, n=n, first=first, last=last)
    else:
        recent_text = t("narrative.execution_recent_fell", lang, n=n, first=first, last=last)
    return f"{lead} {recent_text}"
