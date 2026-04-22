"""Budget by funding source (domestic vs foreign) — 100% stacked bar chart.

Used on the Overview, Education, and Health pages to emphasize how the
foreign-funded share of the budget has evolved over time. Each page
passes in a dataframe already filtered to its country (and, optionally,
its functional category); this component handles the per-year
aggregation, the figure, and the narrative.
"""
import pandas as pd
import plotly.graph_objects as go

from translations import t, genitive
from viz_theme import CENTRAL_COLOR
from utils import empty_plot


# Colors for the 100% stacked funding-source bar. Blue for domestic echoes
# the "central government" palette elsewhere in the dashboard; orange for
# foreign picks up the existing treemap orange so the two bands contrast
# cleanly without clashing.
_DOMESTIC_COLOR = CENTRAL_COLOR
_FOREIGN_COLOR = "#F78D28"


def _aggregate(df, func_filter=None):
    """Collapse func_by_country_year rows into a per-year funding breakdown.

    ``func_filter`` (e.g. ``"Health"``, ``"Education"``) restricts to that
    functional category; omit to aggregate across all categories for the
    overall budget view.

    Returns columns: ``year``, ``budget``, ``domestic_funded_budget``,
    ``foreign_funded_budget``, ``foreign_share_pct``. Drops years where
    either figure is NaN or where total budget ≤ 0.
    """
    empty = pd.DataFrame(
        columns=["year", "budget", "domestic_funded_budget",
                 "foreign_funded_budget", "foreign_share_pct"],
    )
    if df is None or df.empty:
        return empty
    if "budget" not in df.columns or "domestic_funded_budget" not in df.columns:
        return empty

    if func_filter is not None and "func" in df.columns:
        df = df[df["func"] == func_filter]
        if df.empty:
            return empty

    agg = (
        df.groupby("year", as_index=False)[["budget", "domestic_funded_budget"]]
        .agg(lambda x: x.sum(min_count=1))
        .sort_values("year")
    )
    agg["foreign_funded_budget"] = agg["budget"] - agg["domestic_funded_budget"]
    agg = agg.dropna(subset=["budget", "domestic_funded_budget", "foreign_funded_budget"])
    agg = agg[agg["budget"] > 0]
    agg["foreign_share_pct"] = (agg["foreign_funded_budget"] / agg["budget"]) * 100
    return agg


def figure(df, lang="en", func_filter=None):
    """100% stacked bar: domestic vs foreign share of budget, per year."""
    agg = _aggregate(df, func_filter=func_filter)
    if agg.empty:
        return empty_plot(t("error.data_unavailable", lang),
                          fig_title=t("chart.budget_funding_source_over_time", lang))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name=t("trace.domestic_funded", lang),
            x=agg["year"],
            y=agg["domestic_funded_budget"],
            marker_color=_DOMESTIC_COLOR,
            hovertemplate=t("hover.domestic_funded", lang) + ": %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name=t("trace.foreign_funded", lang),
            x=agg["year"],
            y=agg["foreign_funded_budget"],
            marker_color=_FOREIGN_COLOR,
            hovertemplate=t("hover.foreign_funded", lang) + ": %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_yaxes(
        title_text=t("axis.share_of_budget_pct", lang),
        ticksuffix="%",
        range=[0, 100],
    )
    # Years as discrete categories — bars are inherently annual; treating
    # year as a numeric axis would introduce false gaps or spacing bugs.
    fig.update_xaxes(type="category")
    fig.update_layout(
        title=t("chart.budget_funding_source_over_time", lang),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
        hovermode="x unified",
        barmode="stack",
        barnorm="percent",
    )
    return fig


def narrative(df, country, lang="en", func_filter=None):
    """Narrative: period-average split + latest-year foreign share (%)."""
    country_display = t(f"country.{country}", lang)
    country_gen = genitive(lang, country_display)
    agg = _aggregate(df, func_filter=func_filter)
    if agg.empty:
        return t("narrative.funding_source_no_data", lang, country=country_display)

    total_dom = agg["domestic_funded_budget"].sum()
    total_for = agg["foreign_funded_budget"].sum()
    total = total_dom + total_for
    start_year = int(agg["year"].min())
    end_year = int(agg["year"].max())

    if total <= 0 or total_for <= 0:
        text = t("narrative.funding_source_all_domestic", lang, country_gen=country_gen)
    else:
        domestic_pct = (total_dom / total) * 100
        foreign_pct = (total_for / total) * 100
        text = t(
            "narrative.funding_source_summary", lang,
            start_year=start_year, end_year=end_year,
            country_gen=country_gen,
            domestic_pct=domestic_pct, foreign_pct=foreign_pct,
        )

    latest = agg.iloc[-1]
    text += t(
        "narrative.funding_source_latest", lang,
        year=int(latest["year"]),
        foreign_pct=float(latest["foreign_share_pct"]),
    )
    return text
