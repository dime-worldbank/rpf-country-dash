import numpy as np
import plotly.graph_objects as go
from dash import html

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


def _prepare_funding_df(country):
    """Build the per-year domestic/foreign budget split for ``country``.

    Source ``expenditure_w_poverty`` is one row per country-year; domestic =
    ``budget - foreign_funded_budget`` so the two bars sum to the total.

    Deliberately budget-based, not expenditure-based: foreign-sourced
    execution is not tracked for Togo (``foreign_funded_expenditure`` is 0
    for most years), which would render the split as a flat 100% domestic.
    """
    df = server_store.get("expenditure_w_poverty")
    df = filter_country_sort_year(df, country)
    if df.empty or "budget" not in df.columns or "foreign_funded_budget" not in df.columns:
        return df.iloc[0:0]

    df = df.copy()
    # Keep only years with a budget and reported foreign funding; null foreign
    # data means no breakdown, so show nothing rather than imply all-domestic.
    df = df[
        df["budget"].notna()
        & (df["budget"].round(0) != 0)
        & df["foreign_funded_budget"].notna()
    ]
    if df.empty:
        return df

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


def render_fig_and_narrative(country, lang="en", amount="nominal"):
    funding_df = _prepare_funding_df(country)
    if funding_df.empty:
        return (
            empty_plot(t("error.data_unavailable", lang)),
            t("error.data_unavailable", lang),
        )

    basic_info = server_store.get("basic_country_info")[country]
    currency_code = basic_info["currency_code"]

    fig = create_funding_source_figure(funding_df, currency_code, lang=lang, amount=amount)
    narrative = format_funding_source_narrative(funding_df, country, lang=lang)
    return fig, narrative


def create_funding_source_figure(df, currency_code, lang="en", amount="nominal"):
    """``amount`` selects the nominal or the inflation-adjusted budget columns."""
    real = amount == "real"

    def as_currency(values):
        return values.apply(lambda x: format_currency(x, currency_code, lang=lang))

    fig = go.Figure()

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
    total_name = t("trace.total_budget_real" if real else "trace.total_budget", lang)
    fig.add_trace(
        go.Scatter(
            name=total_name,
            x=df["year"],
            y=df[total_col],
            yaxis="y2",
            mode="lines+markers",
            marker_color=TOTAL_BUDGET_COLOR,
            customdata=np.column_stack([as_currency(df[total_col])]),
            hovertemplate="<b>" + total_name + "</b>: %{customdata[0]}<extra></extra>",
        )
    )

    fig.update_xaxes(tickformat="d", dtick=1)
    fig.update_yaxes(
        title_text=t("axis.budget_share", lang),
        ticksuffix="%",
        range=[0, 100],
        fixedrange=True,
    )
    fig.update_layout(
        barmode="stack",
        title=t("chart.budget_by_funding_source", lang),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
        hovermode="x unified",
        yaxis2=dict(
            title_text=t("trace.total_budget", lang),
            overlaying="y",
            side="right",
            showgrid=False,
            rangemode="tozero",
            fixedrange=True,
        ),
    )
    return apply_locale(fig, lang)


def format_funding_source_narrative(df, country, lang="en"):
    country_label = t(f"country.{country}", lang)
    country_gen = genitive(lang, country_label)

    plot_df = df.dropna(subset=["domestic_share"]).sort_values("year")
    mean_domestic = plot_df["domestic_share"].mean()
    average_text = t(
        "narrative.funding_source_average",
        lang,
        country=country_label,
        country_gen=country_gen,
        domestic_share=mean_domestic,
        foreign_share=100 - mean_domestic,
    )

    # Lead with a trend on the domestic share, so the whole narrative reads
    # from one side of the split. Fitting one needs at least two points.
    if len(plot_df) < 2:
        return average_text

    extractor = InsightExtractor(
        plot_df["year"].values,
        plot_df["domestic_share"].values,
        detector=TrendDetector(),
    )
    trend = get_segment_narrative_i18n(
        extractor=extractor,
        metric=t("metric.domestic_funded_share", lang),
        lang=lang,
    )
    if trend:
        trend = trend[0].upper() + trend[1:]
        # Children list rather than "\n": the narrative renders inside an
        # html.P, where a newline character would collapse to a space.
        return [trend, html.Br(), average_text]
    return average_text
