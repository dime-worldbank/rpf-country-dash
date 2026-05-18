"""Revenue / expenditure / fiscal balance chart and narrative.

The feature stitches three sources together on one timeline:

* Official national report (pilot: Togo only)
* GFS_SOO (IMF) — historical fill where official data isn't available
* WEO (IMF) — forward-looking projections

A "composite" view combines all three; single-source views are also available.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from trend_narrative import InsightExtractor, TrendDetector
from utils import add_currency_column, empty_plot, format_currency
from viz_theme import BRIGHT_BLUE, SOLID_BLUE, WARM_BRIGHTER, lighten_color


WEO_SOURCE = "WEO (World Economic Outlook), IMF — General Government"
GFS_SOO_SOURCE = "GFS_SOO (Statement of Operations), IMF — Budgetary Central Government"

REVENUE_COLOR = SOLID_BLUE
EXPENDITURE_COLOR = WARM_BRIGHTER[2]
SURPLUS_COLOR = BRIGHT_BLUE
DEFICIT_COLOR = WARM_BRIGHTER[2]
FORECAST_REVENUE_COLOR = lighten_color(SOLID_BLUE, 0.5)
FORECAST_EXPENDITURE_COLOR = lighten_color(WARM_BRIGHTER[2], 0.5)
DEFICIT_BAR_OPACITY = 0.4


def split_government_budget(gov_df):
    """Split a government_budget frame into ``(gfs_df, weo_df)`` by data source."""
    if gov_df is None or gov_df.empty:
        return None, None
    return (
        gov_df[gov_df["source"] == GFS_SOO_SOURCE],
        gov_df[gov_df["source"] == WEO_SOURCE],
    )


def _balance_bar_colors(series):
    """Blue for surplus (>= 0), red/pink for deficit (< 0)."""
    return [SURPLUS_COLOR if x >= 0 else DEFICIT_COLOR for x in series]


def _clean_rev_exp(df, require_both=False):
    """Sort, coerce numeric, drop empties, attach signed balance.

    ``require_both=True`` drops rows where either revenue or expenditure is
    missing — used for trend analysis, where ``balance`` must be defined.
    ``require_both=False`` keeps rows with one side present — used for
    plotting, where each line can have its own coverage.
    """
    if df is None or df.empty:
        return None
    d = df.copy().sort_values("year")
    d["revenue"] = pd.to_numeric(d["revenue"], errors="coerce")
    d["expenditure"] = pd.to_numeric(d["expenditure"], errors="coerce")
    if require_both:
        d = d.dropna(subset=["revenue", "expenditure"])
    else:
        d = d.dropna(subset=["revenue", "expenditure"], how="all")
    d = d[~((d["revenue"].fillna(0) == 0) & (d["expenditure"].fillna(0) == 0))]
    if d.empty:
        return None
    d["balance"] = d["revenue"] - d["expenditure"]
    return d


# ---- figure ----------------------------------------------------------------

def combined_figure(national_df, gfs_df, weo_df, currency_code, currency_name=None, view_mode="composite"):
    if view_mode == "official":
        gfs_df, weo_df = None, None
    elif view_mode == "gfs":
        national_df, weo_df = gfs_df, None
        gfs_df = None
    elif view_mode == "weo":
        national_df, gfs_df = weo_df, None
        weo_df = None

    national_df = _clean_rev_exp(national_df)
    gfs_df = _clean_rev_exp(gfs_df)
    weo_df = _clean_rev_exp(weo_df)

    has_national = national_df is not None and not national_df.empty
    if has_national:
        national_years = set(national_df["year"].tolist())
        n_min = int(national_df["year"].min())
        n_max = int(national_df["year"].max())
        gfs_pre = (
            gfs_df[(gfs_df["year"] < n_min) & (~gfs_df["year"].isin(national_years))]
            if gfs_df is not None and not gfs_df.empty else None
        )
        weo_post = (
            weo_df[(weo_df["year"] > n_max) & (~weo_df["year"].isin(national_years))]
            if weo_df is not None and not weo_df.empty else None
        )
    else:
        gfs_pre = gfs_df
        if gfs_df is not None and not gfs_df.empty and weo_df is not None and not weo_df.empty:
            gfs_max_year = int(gfs_df["year"].max())
            weo_post = weo_df[weo_df["year"] > gfs_max_year]
        else:
            weo_post = weo_df

    forecast_starts = []
    for src in (gfs_df, weo_df):
        if src is not None and not src.empty and "forecast" in src.columns:
            f = src[src["forecast"].astype(bool)]
            if not f.empty:
                forecast_starts.append(int(f["year"].min()))
    forecast_start_year = (min(forecast_starts) - 1) if forecast_starts else None

    if not has_national and (gfs_pre is None or gfs_pre.empty) and (weo_post is None or weo_post.empty):
        return empty_plot("No revenue budget data available")

    year_bounds = []
    for df in (national_df, gfs_pre, weo_post):
        if df is not None and not df.empty:
            year_bounds.append(int(df["year"].min()))
            year_bounds.append(int(df["year"].max()))
    year_min, year_max = min(year_bounds), max(year_bounds)

    for df in (national_df, gfs_pre, weo_post):
        if df is not None and not df.empty:
            add_currency_column(df, "revenue", currency_code)
            add_currency_column(df, "expenditure", currency_code)
            add_currency_column(df, "balance", currency_code)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.65, 0.35],
        subplot_titles=("Revenue & Expenditure", "Deficit (Revenue − Expenditure)"),
    )

    legend_shown = set()

    def add_series(df, source_label, is_forecast=False, bar_df=None):
        """Emit revenue/expenditure lines and a balance bar for one source.

        ``bar_df`` lets the caller pass a different frame for the bar trace
        than the lines — used by ``add_split`` so the boundary year isn't
        drawn twice in the bar row.
        """
        if df is None or df.empty:
            return
        if bar_df is None:
            bar_df = df

        if is_forecast:
            cat = "forecast"
            label_suffix = " (forecast)"
            rev_color = FORECAST_REVENUE_COLOR
            exp_color = FORECAST_EXPENDITURE_COLOR
            rev_line = dict(color=rev_color, dash="dash", width=2)
            exp_line = dict(color=exp_color, dash="dash", width=2)
            rev_marker = exp_marker = None
            scatter_mode = "lines"
        else:
            cat = "actual"
            label_suffix = ""
            rev_color = REVENUE_COLOR
            exp_color = EXPENDITURE_COLOR
            rev_line = dict(color=rev_color, width=2.5)
            exp_line = dict(color=exp_color, width=2.5)
            rev_marker = dict(color=rev_color, size=7)
            exp_marker = dict(color=exp_color, size=7)
            scatter_mode = "lines+markers"

        def _show_once(key):
            show = key not in legend_shown
            legend_shown.add(key)
            return show

        fig.add_trace(
            go.Scatter(
                name=f"Revenue{label_suffix}",
                legendgroup=f"{cat}_rev",
                showlegend=_show_once(f"{cat}_rev"),
                x=df.year, y=df.revenue,
                mode=scatter_mode,
                line=rev_line,
                marker=rev_marker,
                customdata=df["revenue_formatted"],
                hovertemplate=f"<b>Revenue ({source_label}, {cat})</b>: %{{customdata}}<extra></extra>",
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                name=f"Expenditure{label_suffix}",
                legendgroup=f"{cat}_exp",
                showlegend=_show_once(f"{cat}_exp"),
                x=df.year, y=df.expenditure,
                mode=scatter_mode,
                line=exp_line,
                marker=exp_marker,
                customdata=df["expenditure_formatted"],
                hovertemplate=f"<b>Expenditure ({source_label}, {cat})</b>: %{{customdata}}<extra></extra>",
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Bar(
                name=f"Surplus / Deficit{label_suffix}",
                legendgroup=f"{cat}_def",
                showlegend=_show_once(f"{cat}_def"),
                x=bar_df.year, y=bar_df.balance,
                marker_color=_balance_bar_colors(bar_df.balance),
                opacity=DEFICIT_BAR_OPACITY,
                customdata=bar_df["balance_formatted"],
                hovertemplate=f"<b>Surplus / Deficit ({source_label}, {cat})</b>: %{{customdata}}<extra></extra>",
            ),
            row=2, col=1,
        )

    def add_split(df, source_label):
        """Split a source into actual/forecast traces (lines share the boundary; bars don't)."""
        if df is None or df.empty:
            return
        if "forecast" not in df.columns:
            add_series(df, source_label)
            return
        df = df.sort_values("year")
        actual = df[~df["forecast"].astype(bool)]
        forecast = df[df["forecast"].astype(bool)]
        if not actual.empty and not forecast.empty:
            forecast_lines = pd.concat([actual.tail(1), forecast], ignore_index=True)
        else:
            forecast_lines = forecast
        add_series(actual, source_label, is_forecast=False)
        add_series(forecast_lines, source_label, is_forecast=True, bar_df=forecast)

    add_split(gfs_pre, "GFS")
    add_split(weo_post, "WEO")
    if has_national:
        add_series(national_df, "Official")

    if view_mode == "composite" and forecast_start_year is not None:
        fig.add_shape(
            type="rect",
            xref="x", yref="paper",
            x0=forecast_start_year + 0.5, x1=year_max + 0.5,
            y0=0, y1=1,
            fillcolor="rgba(0,0,0,0.04)",
            line_width=0,
            layer="below",
        )
        fig.add_annotation(
            text="forecast",
            xref="x", yref="paper",
            x=year_max + 0.4, y=0.99,
            xanchor="right", yanchor="top",
            showarrow=False,
            font=dict(size=11, color="gray"),
        )

    x_range = [year_min - 0.5, year_max + 0.5]
    fig.update_xaxes(
        range=x_range,
        tickmode="array",
        tickvals=list(range(year_min, year_max + 1, 2)),
        tickformat="d",
        zeroline=False,
        row=2, col=1,
    )
    fig.update_xaxes(
        range=x_range,
        showticklabels=False,
        zeroline=False,
        row=1, col=1,
    )

    fig.update_yaxes(zeroline=False, row=1, col=1)
    fig.update_yaxes(zeroline=True, zerolinecolor="black", zerolinewidth=1, row=2, col=1)

    y_unit = currency_name or currency_code or ""
    if y_unit:
        fig.add_annotation(
            text=f"Amount ({y_unit})",
            xref="paper", yref="paper",
            x=-0.08, y=0.5,
            textangle=-90,
            showarrow=False,
            font=dict(size=13),
            xanchor="right", yanchor="middle",
        )

    fig.update_layout(
        plot_bgcolor="white",
        hovermode="x unified",
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0),
        barmode="overlay",
        margin=dict(t=80, b=40, l=100, r=40),
    )

    return fig


# ---- narrative ------------------------------------------------------------

def _extract_balance_insights(df):
    """Return ``{"segments": [...], "extrema": {"min": {...}, "max": {...}}}``.

    Segments come from :class:`InsightExtractor` pinned to one segment
    (overall direction). Extrema are pulled from the raw data so brief
    surplus/deficit spikes aren't smoothed away.
    """
    if df is None or len(df) < 2:
        return None
    extractor = InsightExtractor(
        df["year"].values,
        df["balance"].values,
        detector=TrendDetector(max_segments=1),
    )
    segments = extractor.extract_full_suite()["segments"]
    min_idx = df["balance"].idxmin()
    max_idx = df["balance"].idxmax()
    return {
        "segments": segments,
        "extrema": {
            "min": {
                "year": int(df.loc[min_idx, "year"]),
                "value": float(df.loc[min_idx, "balance"]),
            },
            "max": {
                "year": int(df.loc[max_idx, "year"]),
                "value": float(df.loc[max_idx, "balance"]),
            },
        },
    }


def _extract_national_insights(df):
    """Return ``{"year_min", "year_max", "mean_balance", "source_name"}``."""
    if df is None or df.empty:
        return None
    source_name = "the official report"
    if "source" in df.columns:
        sources = df["source"].dropna().unique().tolist()
        if sources:
            source_name = sources[0]
    return {
        "year_min": int(df["year"].min()),
        "year_max": int(df["year"].max()),
        "mean_balance": float(df["balance"].mean()),
        "source_name": source_name,
    }


def _extrema_phrase(extrema, currency_code, forecast=False):
    """Chronologically-ordered phrase joining the largest surplus/deficit."""
    if not extrema:
        return ""

    deficit_label = "the largest projected deficit" if forecast else "the largest deficit"
    surplus_label = "the largest projected surplus" if forecast else "the largest surplus"

    notes = []
    min_e = extrema.get("min")
    if min_e and min_e["value"] < 0:
        notes.append((
            min_e["year"],
            f"{deficit_label} of {format_currency(abs(min_e['value']), currency_code)} "
            f"in {min_e['year']}",
        ))
    max_e = extrema.get("max")
    if max_e and max_e["value"] > 0:
        notes.append((
            max_e["year"],
            f"{surplus_label} of {format_currency(max_e['value'], currency_code)} "
            f"in {max_e['year']}",
        ))

    notes.sort(key=lambda n: n[0])
    phrases = [n[1] for n in notes]
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    return f"{phrases[0]} and {phrases[1]}"


def _period_narrative(prefix, segments, extrema, currency_code, forecast=False):
    """Compose ``'{prefix}, [trend], with [extrema].'``. Empty when no segments."""
    if not segments:
        return ""

    seg = segments[0]
    slope = seg["slope"]
    start_year = int(seg["start_year"])
    end_year = int(seg["end_year"])

    if forecast:
        if slope > 0:
            verb = "is expected to improve overall"
        elif slope < 0:
            verb = "is expected to deteriorate overall"
        else:
            verb = "is expected to remain relatively flat"
    else:
        if slope > 0:
            verb = "improved overall"
        elif slope < 0:
            verb = "deteriorated overall"
        else:
            verb = "remained relatively flat"

    trend = f"between {start_year} and {end_year}, the fiscal balance {verb}"
    extras = _extrema_phrase(extrema, currency_code, forecast=forecast)
    body = f"{trend}, with {extras}" if extras else trend
    return f"{prefix}, {body}."


def _national_narrative(source_name, year_min, year_max, mean_balance, currency_code):
    """Build the ``'The recent official reports from {source_name} indicate ...'`` sentence."""
    if year_min == year_max:
        year_phrase = f"in {year_min}"
    else:
        year_phrase = f"from {year_min} to {year_max}"

    if mean_balance < 0:
        avg_phrase = f"averaged a deficit of {format_currency(abs(mean_balance), currency_code)}"
    elif mean_balance > 0:
        avg_phrase = f"averaged a surplus of {format_currency(mean_balance, currency_code)}"
    else:
        avg_phrase = "averaged a balanced budget"

    return (
        f"The recent official reports from {source_name} indicate "
        f"that the budget {avg_phrase} {year_phrase}."
    )


def narrative(national_df, gfs_df, weo_df, currency_code, view_mode="composite"):
    parts = []

    if view_mode == "official":
        nat = _extract_national_insights(_clean_rev_exp(national_df, require_both=True))
        if nat:
            parts.append(_national_narrative(
                nat["source_name"], nat["year_min"], nat["year_max"],
                nat["mean_balance"], currency_code,
            ))
        return " ".join(parts) if parts else ""

    if view_mode == "gfs":
        gfs = _extract_balance_insights(_clean_rev_exp(gfs_df, require_both=True))
        if gfs:
            parts.append(_period_narrative(
                "Based on GFS data",
                gfs["segments"], gfs["extrema"], currency_code,
            ))
        return " ".join(parts) if parts else ""

    if view_mode == "weo":
        weo = _extract_balance_insights(_clean_rev_exp(weo_df, require_both=True))
        if weo:
            parts.append(_period_narrative(
                "Based on WEO projections",
                weo["segments"], weo["extrema"], currency_code,
                forecast=True,
            ))
        return " ".join(parts) if parts else ""

    # Composite: historical GFS up to national, national, WEO beyond national.
    nat_clean = _clean_rev_exp(national_df, require_both=True)
    nat = _extract_national_insights(nat_clean)
    n_min = nat["year_min"] if nat else None
    n_max = nat["year_max"] if nat else None

    gfs_clean = _clean_rev_exp(gfs_df, require_both=True)
    if gfs_clean is not None and n_min is not None:
        gfs_clean = gfs_clean[gfs_clean["year"] < n_min]
    gfs = _extract_balance_insights(gfs_clean)
    if gfs:
        parts.append(_period_narrative(
            "Based on historical GFS data",
            gfs["segments"], gfs["extrema"], currency_code,
        ))

    if nat:
        parts.append(_national_narrative(
            nat["source_name"], nat["year_min"], nat["year_max"],
            nat["mean_balance"], currency_code,
        ))

    weo_clean = _clean_rev_exp(weo_df, require_both=True)
    if weo_clean is not None and n_max is not None:
        weo_clean = weo_clean[weo_clean["year"] > n_max]
    weo = _extract_balance_insights(weo_clean)
    if weo:
        parts.append(_period_narrative(
            "Looking ahead, WEO projections suggest",
            weo["segments"], weo["extrema"], currency_code,
            forecast=True,
        ))

    return " ".join(parts) if parts else ""
