"""Revenue / expenditure / fiscal balance chart and narrative.

The feature stitches the available sources for a country together on one timeline:

* Official national report (pilot: Togo only) — used where available, takes priority
* GFS_SOO (IMF) — historical fill for years before the official report
* WEO (IMF) — forward-looking projections beyond the official report

The "composite" view layers these on a single timeline; single-source views
("official", "gfs", "weo") show the full record for one source.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from trend_narrative import InsightExtractor, TrendDetector
from translations import t
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


def split_imf_sources(gov_df):
    """Split an IMF government-budget frame into ``(gfs_df, weo_df)`` by data source."""
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

def combined_figure(national_df, gfs_df, weo_df, currency_code, currency_name=None, view_mode="composite", lang="en"):
    if view_mode == "official":
        gfs_df, weo_df = None, None
    elif view_mode == "gfs":
        national_df, weo_df = None, None
    elif view_mode == "weo":
        national_df, gfs_df = None, None

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
        return empty_plot(t("deficit.chart.empty", lang))

    year_bounds = []
    for df in (national_df, gfs_pre, weo_post):
        if df is not None and not df.empty:
            year_bounds.append(int(df["year"].min()))
            year_bounds.append(int(df["year"].max()))
    year_min, year_max = min(year_bounds), max(year_bounds)

    for df in (national_df, gfs_pre, weo_post):
        if df is not None and not df.empty:
            add_currency_column(df, "revenue", currency_code, lang=lang)
            add_currency_column(df, "expenditure", currency_code, lang=lang)
            add_currency_column(df, "balance", currency_code, lang=lang)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.65, 0.35],
        subplot_titles=(
            t("deficit.chart.subplot_revenue_expenditure", lang),
            t("deficit.chart.subplot_balance", lang),
        ),
    )

    revenue_label = t("deficit.chart.revenue", lang)
    expenditure_label = t("deficit.chart.expenditure", lang)
    balance_label = t("deficit.chart.balance", lang)
    forecast_suffix = t("deficit.chart.forecast_suffix", lang)
    actual_kind = t("deficit.chart.actual", lang)
    forecast_kind = t("deficit.chart.forecast", lang)

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
            label_suffix = forecast_suffix
            kind_label = forecast_kind
            rev_color = FORECAST_REVENUE_COLOR
            exp_color = FORECAST_EXPENDITURE_COLOR
            rev_line = dict(color=rev_color, dash="dash", width=2)
            exp_line = dict(color=exp_color, dash="dash", width=2)
            rev_marker = exp_marker = None
            scatter_mode = "lines"
        else:
            cat = "actual"
            label_suffix = ""
            kind_label = actual_kind
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
                name=f"{revenue_label}{label_suffix}",
                legendgroup=f"{cat}_rev",
                showlegend=_show_once(f"{cat}_rev"),
                x=df.year, y=df.revenue,
                mode=scatter_mode,
                line=rev_line,
                marker=rev_marker,
                customdata=df["revenue_formatted"],
                hovertemplate=f"<b>{revenue_label} ({source_label}, {kind_label})</b>: %{{customdata}}<extra></extra>",
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                name=f"{expenditure_label}{label_suffix}",
                legendgroup=f"{cat}_exp",
                showlegend=_show_once(f"{cat}_exp"),
                x=df.year, y=df.expenditure,
                mode=scatter_mode,
                line=exp_line,
                marker=exp_marker,
                customdata=df["expenditure_formatted"],
                hovertemplate=f"<b>{expenditure_label} ({source_label}, {kind_label})</b>: %{{customdata}}<extra></extra>",
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Bar(
                name=f"{balance_label}{label_suffix}",
                legendgroup=f"{cat}_def",
                showlegend=_show_once(f"{cat}_def"),
                x=bar_df.year, y=bar_df.balance,
                marker_color=_balance_bar_colors(bar_df.balance),
                opacity=DEFICIT_BAR_OPACITY,
                customdata=bar_df["balance_formatted"],
                hovertemplate=f"<b>{balance_label} ({source_label}, {kind_label})</b>: %{{customdata}}<extra></extra>",
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

    add_split(gfs_pre, t("deficit.chart.source_gfs", lang))
    add_split(weo_post, t("deficit.chart.source_weo", lang))
    if has_national:
        add_series(national_df, t("deficit.chart.source_official", lang))

    if forecast_start_year is not None:
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
            text=t("deficit.chart.forecast_band", lang),
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
            text=t("deficit.chart.amount_axis", lang, unit=y_unit),
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
    """Return ``{"trend": {...} | None, "extrema": {"min": {...}, "max": {...}}}``.

    The ``trend`` dict has primitive fields (``start_year``, ``end_year``,
    ``slope``) — this is the only place that knows trend_narrative's
    segment shape, so swapping the package later only touches this function.

    Extrema are pulled from the raw data so brief surplus/deficit spikes
    aren't smoothed away by the segmentation.
    """
    if df is None or len(df) < 2:
        return None
    extractor = InsightExtractor(
        df["year"].values,
        df["balance"].values,
        detector=TrendDetector(max_segments=1),
    )
    segments = extractor.extract_full_suite()["segments"]
    trend = None
    if segments:
        seg = segments[0]
        trend = {
            "start_year": int(seg["start_year"]),
            "end_year": int(seg["end_year"]),
            "slope": seg["slope"],
        }
    min_idx = df["balance"].idxmin()
    max_idx = df["balance"].idxmax()
    return {
        "trend": trend,
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
    """Return ``{"year_min", "year_max", "mean_balance", "source_name"}``.

    ``source_name`` is ``None`` when the frame has no ``source`` column or all
    rows are null — the caller substitutes a localized default.
    """
    if df is None or df.empty:
        return None
    source_name = None
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


def _extrema_phrase(extrema, currency_code, forecast=False, lang="en"):
    """Chronologically-ordered phrase joining the largest surplus/deficit."""
    if not extrema:
        return ""

    deficit_key = "deficit.narrative.extrema.deficit_forecast" if forecast else "deficit.narrative.extrema.deficit"
    surplus_key = "deficit.narrative.extrema.surplus_forecast" if forecast else "deficit.narrative.extrema.surplus"
    deficit_label = t(deficit_key, lang)
    surplus_label = t(surplus_key, lang)

    notes = []
    min_e = extrema.get("min")
    if min_e and min_e["value"] < 0:
        notes.append((
            min_e["year"],
            t("deficit.narrative.extrema.entry", lang,
              label=deficit_label,
              amount=format_currency(abs(min_e["value"]), currency_code, lang=lang),
              year=min_e["year"]),
        ))
    max_e = extrema.get("max")
    if max_e and max_e["value"] > 0:
        notes.append((
            max_e["year"],
            t("deficit.narrative.extrema.entry", lang,
              label=surplus_label,
              amount=format_currency(max_e["value"], currency_code, lang=lang),
              year=max_e["year"]),
        ))

    notes.sort(key=lambda n: n[0])
    phrases = [n[1] for n in notes]
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    return t("deficit.narrative.extrema.joiner", lang).join(phrases)


def _period(prefix, trend, extrema, currency_code, forecast=False, lang="en"):
    """Compose the trend-period sentence for one data source."""
    if not trend:
        return ""

    slope = trend["slope"]
    if forecast:
        verb_key = (
            "deficit.narrative.verb.improved_forecast" if slope > 0 else
            "deficit.narrative.verb.deteriorated_forecast" if slope < 0 else
            "deficit.narrative.verb.flat_forecast"
        )
    else:
        verb_key = (
            "deficit.narrative.verb.improved" if slope > 0 else
            "deficit.narrative.verb.deteriorated" if slope < 0 else
            "deficit.narrative.verb.flat"
        )
    verb = t(verb_key, lang)
    extras = _extrema_phrase(extrema, currency_code, forecast=forecast, lang=lang)

    if forecast:
        template_key = "deficit.narrative.period_forecast_with_extras" if extras else "deficit.narrative.period_forecast_no_extras"
    else:
        template_key = "deficit.narrative.period_with_extras" if extras else "deficit.narrative.period_no_extras"
    return t(
        template_key, lang,
        prefix=prefix,
        start_year=trend["start_year"],
        end_year=trend["end_year"],
        verb=verb,
        extras=extras,
    )


_SOURCE_NAME_KEYS = {
    "Togo DGB Budget Execution Report": "deficit.narrative.source.togo_dgb_budget_execution",
    # Add more as country data lands. Unknown source values pass through untranslated.
}


def _localize_source(source_name, lang):
    """Translate a known database source name; pass through unknown values."""
    if not source_name:
        return None
    key = _SOURCE_NAME_KEYS.get(source_name)
    return t(key, lang) if key else source_name


def _national(source_name, year_min, year_max, mean_balance, currency_code, lang="en"):
    """Build the ``'The recent official reports from {source_name} indicate ...'`` sentence."""
    source_name = _localize_source(source_name, lang)
    if not source_name:
        source_name = t("deficit.narrative.default_source", lang)

    if year_min == year_max:
        year_phrase = t("deficit.narrative.year_single", lang, year=year_min)
    else:
        year_phrase = t("deficit.narrative.year_range", lang, start=year_min, end=year_max)

    if mean_balance < 0:
        avg_phrase = t("deficit.narrative.avg_deficit", lang,
                       amount=format_currency(abs(mean_balance), currency_code, lang=lang))
    elif mean_balance > 0:
        avg_phrase = t("deficit.narrative.avg_surplus", lang,
                       amount=format_currency(mean_balance, currency_code, lang=lang))
    else:
        avg_phrase = t("deficit.narrative.avg_balanced", lang)

    return t("deficit.narrative.national", lang,
             source_name=source_name, avg_phrase=avg_phrase, year_phrase=year_phrase)


def narrative(national_df, gfs_df, weo_df, currency_code, view_mode="composite", lang="en"):
    parts = []

    if view_mode == "official":
        nat = _extract_national_insights(_clean_rev_exp(national_df, require_both=True))
        if nat:
            parts.append(_national(
                nat["source_name"], nat["year_min"], nat["year_max"],
                nat["mean_balance"], currency_code, lang=lang,
            ))
        return " ".join(parts) if parts else ""

    if view_mode == "gfs":
        gfs = _extract_balance_insights(_clean_rev_exp(gfs_df, require_both=True))
        if gfs:
            parts.append(_period(
                t("deficit.narrative.prefix.gfs", lang),
                gfs["trend"], gfs["extrema"], currency_code, lang=lang,
            ))
        return " ".join(parts) if parts else ""

    if view_mode == "weo":
        weo = _extract_balance_insights(_clean_rev_exp(weo_df, require_both=True))
        if weo:
            parts.append(_period(
                t("deficit.narrative.prefix.weo", lang),
                weo["trend"], weo["extrema"], currency_code,
                forecast=True, lang=lang,
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
        parts.append(_period(
            t("deficit.narrative.prefix.gfs_historical", lang),
            gfs["trend"], gfs["extrema"], currency_code, lang=lang,
        ))

    if nat:
        parts.append(_national(
            nat["source_name"], nat["year_min"], nat["year_max"],
            nat["mean_balance"], currency_code, lang=lang,
        ))

    weo_clean = _clean_rev_exp(weo_df, require_both=True)
    if weo_clean is not None and n_max is not None:
        weo_clean = weo_clean[weo_clean["year"] > n_max]
    weo = _extract_balance_insights(weo_clean)
    if weo:
        parts.append(_period(
            t("deficit.narrative.prefix.weo_lookahead", lang),
            weo["trend"], weo["extrema"], currency_code,
            forecast=True, lang=lang,
        ))

    return " ".join(parts) if parts else ""
