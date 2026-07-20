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

from constants import (
    WEO_SOURCE,
    GFS_SOO_SOURCE,
    VIEW_COMPOSITE,
    VIEW_OFFICIAL,
    VIEW_GFS,
    VIEW_WEO,
)
from trend_narrative import InsightExtractor, TrendDetector
from translations import t
from utils import add_currency_column, empty_plot, format_currency, apply_locale
from viz_theme import SOLID_BLUE, WARM_BRIGHTER

REVENUE_COLOR = SOLID_BLUE
EXPENDITURE_COLOR = WARM_BRIGHTER[2]
BALANCE_BAR_OPACITY = 0.4
# Pinned so a sparse surplus/deficit trace isn't auto-sized into overly wide bars.
BALANCE_BAR_WIDTH = 0.7

# Fixed legend order keyed by legendgroup: each line sits next to its forecast
# (they share a hue, differing only by dash), balance bars last.
LEGEND_RANK = {
    "actual_rev": 1,
    "forecast_rev": 2,
    "actual_exp": 3,
    "forecast_exp": 4,
    "surplus": 5,
    "deficit": 6,
}


def split_imf_sources(gov_df):
    """Split an IMF government revenue/expenditure frame into ``(gfs_df, weo_df)`` by data source."""
    if gov_df is None or gov_df.empty:
        return None, None
    return (
        gov_df[gov_df["source"] == GFS_SOO_SOURCE],
        gov_df[gov_df["source"] == WEO_SOURCE],
    )


def _clean_rev_exp(df):
    """Sort, coerce numeric, and keep rows where both revenue/expenditure exist.

    Fiscal-balance analysis and charting require both series for each year,
    so rows missing either side are dropped before balance is computed.
    """
    if df is None or df.empty:
        return None
    d = df.copy().sort_values("year")
    d["revenue"] = pd.to_numeric(d["revenue"], errors="coerce")
    d["expenditure"] = pd.to_numeric(d["expenditure"], errors="coerce")
    if "tax_expenditure" in d.columns:
        # Drop years where tax expenditure wasn't reported (0 is a valid value);
        # subtract it from both sides so totals are comparable to GFS/WEO.
        d["tax_expenditure"] = pd.to_numeric(d["tax_expenditure"], errors="coerce")
        d = d[d["tax_expenditure"].notna()]
        d["revenue"] = d["revenue"] - d["tax_expenditure"]
        d["expenditure"] = d["expenditure"] - d["tax_expenditure"]
    d = d.dropna(subset=["revenue", "expenditure"])
    d = d[~((d["revenue"] == 0) & (d["expenditure"] == 0))]
    if d.empty:
        return None
    d["balance"] = d["revenue"] - d["expenditure"]
    return d


def _none_if_empty(df):
    return None if df is None or df.empty else df


def _frames_for_view(national_df, gfs_df, weo_df, view_mode=VIEW_COMPOSITE):
    """Return view-specific frames after applying source-priority year windows."""
    national_df = _none_if_empty(national_df)
    gfs_df = _none_if_empty(gfs_df)
    weo_df = _none_if_empty(weo_df)

    if view_mode == VIEW_OFFICIAL:
        return national_df, None, None
    if view_mode == VIEW_GFS:
        return None, gfs_df, None
    if view_mode == VIEW_WEO:
        return None, None, weo_df

    # Composite: national has priority, GFS fills pre-national years,
    # and WEO covers post-national years (or post-GFS if no national).
    n_min = n_max = None
    if national_df is not None:
        n_min = int(national_df["year"].min())
        n_max = int(national_df["year"].max())

    gfs_end_year = None
    if gfs_df is not None:
        gfs_end_year = (n_min - 1) if n_min is not None else int(gfs_df["year"].max())
        gfs_df = gfs_df[gfs_df["year"] <= gfs_end_year]

    if weo_df is not None:
        if n_max is not None:
            weo_df = weo_df[weo_df["year"] > n_max]
        elif gfs_end_year is not None:
            weo_df = weo_df[weo_df["year"] > gfs_end_year]

    return _none_if_empty(national_df), _none_if_empty(gfs_df), _none_if_empty(weo_df)


# ---- figure ----------------------------------------------------------------

def combined_figure(national_df, gfs_df, weo_df, currency_code, currency_name=None, view_mode=VIEW_COMPOSITE, lang="en"):
    national_df = _clean_rev_exp(national_df)
    gfs_df = _clean_rev_exp(gfs_df)
    weo_df = _clean_rev_exp(weo_df)
    national_df, gfs_pre, weo_post = _frames_for_view(
        national_df, gfs_df, weo_df, view_mode=view_mode
    )

    has_national = national_df is not None and not national_df.empty

    forecast_start_year = None
    if weo_post is not None and not weo_post.empty and "is_forecast" in weo_post.columns:
        f = weo_post[weo_post["is_forecast"].astype(bool)]
        if not f.empty:
            forecast_start_year = int(f["year"].min()) - 1

    if not has_national and (gfs_pre is None or gfs_pre.empty) and (weo_post is None or weo_post.empty):
        return empty_plot(t("error.no_data_available", lang))

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
    )

    revenue_label = t("deficit.chart.revenue", lang)
    expenditure_label = t("deficit.chart.expenditure", lang)
    surplus_label = t("deficit.chart.surplus", lang)
    deficit_label = t("deficit.chart.deficit", lang)
    forecast_suffix = t("deficit.chart.forecast_suffix", lang)
    actual_kind = t("deficit.chart.actual", lang)
    forecast_kind = t("deficit.chart.forecast", lang)

    legend_shown = set()

    def add_series(df, source_label, is_forecast=False):
        """Emit revenue/expenditure lines and a balance bar for one source."""
        if df is None or df.empty:
            return

        if is_forecast:
            cat = "forecast"
            label_suffix = forecast_suffix
            kind_label = forecast_kind
            rev_line = dict(color=REVENUE_COLOR, dash="dash", width=2)
            exp_line = dict(color=EXPENDITURE_COLOR, dash="dash", width=2)
            rev_marker = exp_marker = None
            scatter_mode = "lines"
        else:
            cat = "actual"
            label_suffix = ""
            kind_label = actual_kind
            rev_line = dict(color=REVENUE_COLOR, width=2.5)
            exp_line = dict(color=EXPENDITURE_COLOR, width=2.5)
            rev_marker = dict(color=REVENUE_COLOR, size=7)
            exp_marker = dict(color=EXPENDITURE_COLOR, size=7)
            scatter_mode = "lines+markers"

        def _show_once(key):
            show = key not in legend_shown
            legend_shown.add(key)
            return show

        fig.add_trace(
            go.Scatter(
                name=f"{revenue_label}{label_suffix}",
                legendgroup=f"{cat}_rev",
                legendrank=LEGEND_RANK[f"{cat}_rev"],
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
                legendrank=LEGEND_RANK[f"{cat}_exp"],
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
        # Split the balance bar into surplus/deficit traces so each gets its own
        # correctly-colored legend entry. Both share a legendgroup across every
        # source and across actual/forecast, so surplus and deficit each appear
        # once regardless of how the timeline is stitched together. Each reuses
        # its revenue/expenditure line hue, kept distinct by the bar opacity.
        for seg_df, seg_color, seg_key, seg_label in (
            (df[df.balance >= 0], REVENUE_COLOR, "surplus", surplus_label),
            (df[df.balance < 0], EXPENDITURE_COLOR, "deficit", deficit_label),
        ):
            if seg_df.empty:
                continue
            fig.add_trace(
                go.Bar(
                    name=seg_label,
                    legendgroup=seg_key,
                    legendrank=LEGEND_RANK[seg_key],
                    showlegend=_show_once(seg_key),
                    x=seg_df.year, y=seg_df.balance,
                    width=BALANCE_BAR_WIDTH,
                    marker_color=seg_color,
                    opacity=BALANCE_BAR_OPACITY,
                    customdata=seg_df["balance_formatted"],
                    hovertemplate=f"<b>{seg_label} ({source_label}, {kind_label})</b>: %{{customdata}}<extra></extra>",
                ),
                row=2, col=1,
            )

    def add_weo_split(df, source_label):
        """Split WEO into actual and forecast traces.

        The boundary year belongs to the actual series. A separate hover-free
        dashed connector bridges it to the first forecast point, so the line
        stays continuous without that year being tagged both actual and forecast.
        """
        if df is None or df.empty:
            return
        if "is_forecast" not in df.columns:
            add_series(df, source_label)
            return
        df = df.sort_values("year")
        actual = df[~df["is_forecast"].astype(bool)]
        forecast = df[df["is_forecast"].astype(bool)]
        add_series(actual, source_label, is_forecast=False)
        add_series(forecast, source_label, is_forecast=True)
        if not actual.empty and not forecast.empty:
            bridge = pd.concat([actual.tail(1), forecast.head(1)], ignore_index=True)
            for col, color in (
                ("revenue", REVENUE_COLOR),
                ("expenditure", EXPENDITURE_COLOR),
            ):
                fig.add_trace(
                    go.Scatter(
                        x=bridge.year, y=bridge[col],
                        mode="lines",
                        line=dict(color=color, dash="dash", width=2),
                        showlegend=False,
                        hoverinfo="skip",
                    ),
                    row=1, col=1,
                )

    add_series(gfs_pre, t("deficit.chart.source_gfs", lang))
    add_weo_split(weo_post, t("deficit.chart.source_weo", lang))
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
        title=dict(text=t("chart.fiscal_balance_over_time", lang), x=0.5, xanchor="center", y=0.97, yref="container", yanchor="top"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        barmode="overlay",
        margin=dict(t=70, b=40, l=100, r=40),
    )

    return apply_locale(fig, lang=lang)


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


def _build_period_sentence(prefix, trend, extrema, currency_code, forecast=False, lang="en"):
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


def _finalize_parts(parts):
    return " ".join(parts) if parts else ""


def _append_period_from_df(parts, prefix, df, currency_code, forecast=False, lang="en"):
    insights = _extract_balance_insights(df)
    if not insights:
        return
    parts.append(_build_period_sentence(
        prefix,
        insights["trend"], insights["extrema"], currency_code,
        forecast=forecast, lang=lang,
    ))


def _append_weo_periods(parts, weo_df, currency_code, lang="en", composite_mode=False):
    """Append WEO narrative sentence(s), splitting actual/forecast when available."""
    if weo_df is None:
        return

    if "is_forecast" not in weo_df.columns:
        prefix = t("deficit.narrative.prefix.weo_lookahead", lang) if composite_mode else t("deficit.narrative.prefix.weo", lang)
        _append_period_from_df(parts, prefix, weo_df, currency_code, forecast=composite_mode, lang=lang)
        return

    forecast_mask = weo_df["is_forecast"].astype(bool)
    has_actual = (~forecast_mask).any()
    has_forecast = forecast_mask.any()

    if has_actual:
        _append_period_from_df(
            parts,
            t("deficit.narrative.prefix.weo", lang),
            weo_df[~forecast_mask],
            currency_code,
            forecast=False,
            lang=lang,
        )

    if has_forecast:
        forecast_prefix = (
            t("deficit.narrative.prefix.weo_lookahead", lang)
            if composite_mode or has_actual else
            t("deficit.narrative.prefix.weo", lang)
        )
        _append_period_from_df(
            parts,
            forecast_prefix,
            weo_df[forecast_mask],
            currency_code,
            forecast=True,
            lang=lang,
        )


def narrative(national_df, gfs_df, weo_df, currency_code, view_mode=VIEW_COMPOSITE, lang="en"):
    parts = []

    national_df = _clean_rev_exp(national_df)
    gfs_df = _clean_rev_exp(gfs_df)
    weo_df = _clean_rev_exp(weo_df)
    nat_view, gfs_view, weo_view = _frames_for_view(
        national_df, gfs_df, weo_df, view_mode=view_mode
    )

    if view_mode == VIEW_OFFICIAL:
        nat = _extract_national_insights(nat_view)
        if nat:
            parts.append(_national(
                nat["source_name"], nat["year_min"], nat["year_max"],
                nat["mean_balance"], currency_code, lang=lang,
            ))
        return _finalize_parts(parts)

    if view_mode == VIEW_GFS:
        _append_period_from_df(
            parts,
            t("deficit.narrative.prefix.gfs", lang),
            gfs_view,
            currency_code,
            lang=lang,
        )
        return _finalize_parts(parts)

    if view_mode == VIEW_WEO:
        _append_weo_periods(parts, weo_view, currency_code, lang=lang, composite_mode=False)
        return _finalize_parts(parts)

    # Composite: historical GFS up to national, national, WEO beyond national.
    nat = _extract_national_insights(nat_view)
    _append_period_from_df(
        parts,
        t("deficit.narrative.prefix.gfs_historical", lang),
        gfs_view,
        currency_code,
        lang=lang,
    )

    if nat:
        parts.append(_national(
            nat["source_name"], nat["year_min"], nat["year_max"],
            nat["mean_balance"], currency_code, lang=lang,
        ))

    _append_weo_periods(parts, weo_view, currency_code, lang=lang, composite_mode=True)

    return _finalize_parts(parts)
