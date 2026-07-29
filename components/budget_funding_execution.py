import numpy as np
import plotly.graph_objects as go

from translations import t, genitive
from trend_narrative import InsightExtractor, TrendDetector
from trend_narrative_i18n import get_segment_narrative_i18n
from constants import translate_econ
from components.func_operational_vs_capital_spending import CAPEX, OP_WAGE_BILL
from viz_theme import QUALITATIVE, lighten_color
from utils import (
    apply_locale,
    empty_plot,
    filter_country_sort_year,
    format_currency,
)
import server_store

# Kept off blue: total_figure above uses the central-government blue.
DOMESTIC_FUNDED_COLOR = "#8E6BA6"  # dusty violet
FOREIGN_FUNDED_COLOR = "#E0AE3C"  # gold
TOTAL_BUDGET_COLOR = "#3A3F47"  # charcoal

REFERENCE_LINE_COLOR = "#8A8F98"  # slate gray

# --- Budget execution ("How much of the budget is spent?") ------------------
#
# What the chart has to do:
#   1. Show each year's execution rate (spending / approved budget), or the
#      same figure as its deviation from 100%, whichever the radio selects.
#   2. Make the *distance from 100%* the thing the eye measures — that gap is
#      what PEFA PI-1 grades — hence a lollipop per year rather than a bar.
#   3. Grade that distance: A/B/C bands within ±5/10/15%, D past that, shaded
#      behind the marks and lettered on the right-hand axis.
#   4. Hold the same window on every country and sector, so a given distance
#      always looks the same; show the years past it without letting them set
#      the scale.
#   5. Say it in the reader's language, and say "unavailable" when it is.
#
# PEFA PI-1 grades on 2 of the last 3 years; this dashboard applies the
# threshold per year. Bands nest: A inside B inside C. https://www.pefa.org/node/4762
PEFA_A_BAND = (95, 105)
PEFA_B_BAND = (90, 110)
PEFA_C_BAND = (85, 115)
CREDIBLE_BAND = PEFA_A_BAND  # the narrative's credible/not-credible cutoff
# The window (req. 4) and the blank gutter held outside it, where an off-scale
# year's arrow goes — far enough out to read as off the chart, not a near miss.
PEFA_PLOT_RANGE = (80, 120)
PEFA_OFF_SCALE_GUTTER = 6

# (letter, band, tint), widest first — the drawing order the nesting needs, and
# the source of both the shading and the axis letters. Tints are the PEFA tier
# hues blended toward white; D keeps the most color, so the worst years land in
# a zone that looks like a verdict rather than blank paper.
_SEA_GREEN, _AMBER, _TERRACOTTA = "#2E8B6B", "#C8781E", "#C0503A"
PEFA_ZONES = (
    ("D", PEFA_PLOT_RANGE, lighten_color(_TERRACOTTA, 0.70)),
    ("C", PEFA_C_BAND, lighten_color(_TERRACOTTA, 0.85)),
    ("B", PEFA_B_BAND, lighten_color(_AMBER, 0.85)),
    ("A", PEFA_A_BAND, lighten_color(_SEA_GREEN, 0.85)),
)
# The zone behind a dot names its tier, so the marks are one neutral ink.
EXECUTION_MARK_COLOR = TOTAL_BUDGET_COLOR
MARK_RING = dict(color="white", width=2)  # holds a mark's edge against its zone
PEFA_REFERENCE_COLOR = "#4A5058"  # dark slate
PEFA_LABEL_COLOR = "#6B7078"  # muted: the rating axis labels the background


def _scoped_frame(country, sector):
    """One country's rows: the national table, or one sector's of the functional one."""
    if sector:
        df = server_store.get("func_by_country_year")
        df = df[df["func"] == sector]
    else:
        df = server_store.get("expenditure_w_poverty")
    return filter_country_sort_year(df, country)


def _prepare_funding_df(df):
    """Funding split + real-terms columns from a country(-sector)-scoped frame."""
    if df.empty or "budget" not in df.columns:
        return df.iloc[0:0]
    return _add_funding_columns(df)


def _add_funding_columns(df):
    """Domestic/foreign split + real-terms columns for a scoped budget frame.

    Data structure checks are centralized in ``data_mapping``; this function
    assumes funding columns already exist and uses them directly.
    """
    df = df.copy()
    df = df[df["budget"].notna() & (df["budget"].round(0) != 0)]
    if df.empty:
        return df
    df["domestic_share"] = df["domestic_funded_budget"] / df["budget"] * 100
    df["foreign_share"] = df["foreign_funded_budget"] / df["budget"] * 100
    return df.sort_values("year")


# Trend fit runs a slow, deterministic global optimiser (~90ms); memoise per
# (country, lang, terms, sector) so toggling the radio doesn't refit it.
_FUNDING_CACHE = {}


def render_funding(country, lang="en", budget_terms="nominal", sector=None):
    """Figure and narrative together, so one callback updates both in one round-trip.

    ``sector`` scopes to a functional sector (None = national). Memoised.
    """
    key = (country, lang, budget_terms, sector)
    if key not in _FUNDING_CACHE:
        _FUNDING_CACHE[key] = _build_funding(country, lang, budget_terms, sector)
    return _FUNDING_CACHE[key]


def clear_cache():
    """Drop memoised results so a data refresh isn't served stale narratives."""
    _FUNDING_CACHE.clear()


def _build_funding(country, lang, budget_terms, sector):
    funding_df = _prepare_funding_df(_scoped_frame(country, sector))
    if funding_df.empty:
        unavailable = t("error.data_unavailable", lang)
        return empty_plot(unavailable), unavailable
    currency_code = server_store.get("basic_country_info")[country]["currency_code"]
    budget_label = None
    if sector:
        phrase = _sector_budget_phrase(sector, lang, real=False)
        budget_label = phrase[0].upper() + phrase[1:]
    fig = create_funding_source_figure(
        funding_df, currency_code, lang=lang, budget_terms=budget_terms, budget_label=budget_label
    )
    narrative = format_funding_source_narrative(
        funding_df, country, lang=lang, budget_terms=budget_terms, sector=sector
    )
    return fig, narrative


def render_execution_narrative(country, lang="en", sector=None):
    execution_df = _execution_df(country, sector)
    if execution_df.empty:
        return t("error.data_unavailable", lang)
    narrative = format_execution_narrative(execution_df, country, lang=lang, sector=sector)
    if sector:
        econ_df = _prepare_econ_execution_df(country, sector)
        clause = _format_econ_execution_clause(econ_df, sector, lang=lang)
        if clause:
            narrative = f"{narrative} {clause}"
    return narrative


def create_funding_source_figure(
    df, currency_code, lang="en", budget_terms="nominal", budget_label=None
):
    """Total-budget line, plus the domestic/foreign split where it's available.

    A country reporting only a total gets a plain line, not an empty chart.
    ``budget_label`` names the total line (e.g. "Education budget").
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
    # Constant label: a real-terms variant would wrap the legend into the title.
    total_name = budget_label or t("trace.total_budget", lang)
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
        fig.update_yaxes(title_text=total_name, rangemode="tozero", fixedrange=True)
        fig.update_layout(title=t("chart.total_budget_over_time", lang), showlegend=False)

    fig.update_layout(
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
        hovermode="x unified",
    )
    return apply_locale(fig, lang)


def _sector_budget_phrase(sector, lang, real):
    sector_name = t(f"sector.{sector.lower()}", lang)
    key = "phrase.sector_budget_real" if real else "phrase.sector_budget"
    return t(key, lang, sector=sector_name, sector_gen=genitive(lang, sector_name))


def _budget_metric(sector, lang, real):
    if not sector:
        return t("metric.total_budget_real" if real else "metric.total_budget", lang)
    phrase = _sector_budget_phrase(sector, lang, real)
    if lang == "en":
        return phrase
    # "orçamento" / "budget" are masculine, so the metric dict is masculine.
    return {"name": ("o " if lang == "pt" else "le ") + phrase, "plural": False, "feminine": False}


def _budget_label(sector, lang):
    """Lowercase, mid-sentence budget noun: 'budget', or '{sector} budget'."""
    if not sector:
        return t("radio.budget", lang).lower()
    return _sector_budget_phrase(sector, lang, real=False)


def format_funding_source_narrative(df, country, lang="en", budget_terms="nominal", sector=None):
    country_label = t(f"country.{country}", lang)

    real = budget_terms == "real"
    total_col = "real_budget" if real else "budget"
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
            metric=_budget_metric(sector, lang, real),
            lang=lang,
        )
        if trend:
            trend = trend[0].upper() + trend[1:]

    # State the split as unknown rather than dropping it silently — silence
    # would read as "no foreign funding". The trend above already covers the total.
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


def _execution_df(country, sector=None):
    """Per-year budget execution for ``country``, nationally or for one sector."""
    return _add_execution_columns(_scoped_frame(country, sector))


def _add_execution_columns(df):
    """Execution rate and variance; filters on expenditure (not the split), so it
    keeps years the funding chart drops."""
    if df.empty or not {"budget", "expenditure"}.issubset(df.columns):
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


def render_execution_figure(country, lang="en", metric="execution_rate", sector=None):
    execution_df = _execution_df(country, sector)
    if execution_df.empty:
        return empty_plot(t("error.data_unavailable", lang))
    return create_execution_figure(execution_df, lang=lang, metric=metric)


def _metric_fields(metric, lang):
    """(column, offset from rate space, axis title) for the metric on show.

    Variance is rate - 100, so the whole rate-space scale — bands, reference
    line, zone edges — shifts by that offset when it's the metric selected.
    """
    if metric == "variance":
        return "execution_variance", 100, t("axis.execution_variance", lang)
    return "execution_rate", 0, t("axis.execution_rate", lang)


def _stem_trace(years, values, reference):
    """The reference-to-value stems as one trace; the dots on top own the hover."""
    xs, ys = [], []
    for year, value in zip(years, values):
        # None breaks the line between stems so they don't join up.
        xs += [year, year, None]
        ys += [reference, value, None]
    return go.Scatter(
        name="stems",
        x=xs,
        y=ys,
        mode="lines",
        # A connector, not the reading: thin and faint enough to sit under the
        # reference line and the dot without competing with either.
        line=dict(color=EXECUTION_MARK_COLOR, width=1.2),
        opacity=0.45,
        hoverinfo="skip",
        showlegend=False,
    )


def _off_scale_trace(years, values, pinned, last_year):
    """The off-scale years, as arrows at their pinned position in the gutter.

    Each carries its real figure as a label, since the axis can't be read for it.
    """
    above = values.to_numpy() > pinned
    return go.Scatter(
        name="off_scale",
        x=years,
        y=pinned,
        mode="markers+text",
        marker=dict(
            color=EXECUTION_MARK_COLOR,
            size=13,
            symbol=np.where(above, "triangle-up", "triangle-down"),
            line=MARK_RING,
        ),
        text=[f"{value:.0f}%" for value in values],
        # Beside the arrow: the stem arrives from one side and the plot edge is
        # on the other. The last year flips left, having no room to its right.
        textposition=np.where(years >= last_year, "middle left", "middle right"),
        textfont=dict(color=EXECUTION_MARK_COLOR, size=11),
        customdata=values,
        hovertemplate="%{x}: %{customdata:.1f}%<extra></extra>",
        showlegend=False,
    )


def _zone_shapes_and_ticks(offset):
    """The zone rects, widest first, and the (y, letter) ticks that name them.

    Both come off ``PEFA_ZONES`` in one pass. Each narrower rect paints over the
    middle of the one before it, exactly as the ratings nest. A letter goes at
    the middle of the strip its zone adds to the one inside it — 105-110 for B,
    and so on — plus that strip's mirror below the reference line; A, which the
    line runs through, is lettered once, on it.
    """
    shapes = [
        dict(
            type="rect",
            xref="x domain", x0=0, x1=1,
            yref="y", y0=low - offset, y1=high - offset,
            fillcolor=tint, line_width=0, layer="below",
        )
        for _, (low, high), tint in PEFA_ZONES
    ]
    ticks = [(100 - offset, PEFA_ZONES[-1][0])]
    for (letter, (_, outer), _), (_, (_, inner), _) in zip(PEFA_ZONES, PEFA_ZONES[1:]):
        middle = (inner + outer) / 2
        ticks += [(middle - offset, letter), (200 - middle - offset, letter)]
    return shapes, sorted(ticks)


def _rating_axis(ticks, lang):
    """The right-hand axis: the rating letters, against the zones they name."""
    return dict(
        # The indicator's number alone doesn't say what it measures, so the
        # title spells it out — the letters beside it are the score.
        title=dict(text=t("axis.pefa_pi1", lang)),
        overlaying="y",
        side="right",
        matches="y",  # the letters mislabel their zones if the two scales drift
        fixedrange=True,
        ticks="",
        tickmode="array",
        tickvals=[y for y, _ in ticks],
        ticktext=[letter for _, letter in ticks],
        tickfont=dict(color=PEFA_LABEL_COLOR, size=11),
        title_font=dict(color=PEFA_LABEL_COLOR),
    )


def create_execution_figure(df, lang="en", metric="execution_rate"):
    """``metric`` selects the ``execution_rate`` or its ``variance`` from budget.

    Each year is a lollipop: a stem from the reference line to a dot at the
    value, so the distance the PEFA bands are about is what the eye measures.
    """
    col, offset, axis = _metric_fields(metric, lang)
    reference = 100 - offset
    zone_low, zone_high = PEFA_PLOT_RANGE[0] - offset, PEFA_PLOT_RANGE[1] - offset
    gutter = PEFA_OFF_SCALE_GUTTER
    values = df[col]
    off_scale = (values < zone_low) | (values > zone_high)
    # Off-scale years are pinned to the middle of the gutter — as far as their
    # stems run, so a year that misses by 200% takes up no more of the plot than
    # one that misses by 41%.
    pinned = np.clip(values.to_numpy(), zone_low - gutter / 2, zone_high + gutter / 2)

    marks = [
        # plotly only draws an overlaying axis that some trace sits on, and the
        # rating axis has no data of its own.
        go.Scatter(x=[None], y=[None], yaxis="y2", mode="markers", showlegend=False),
        _stem_trace(df["year"], pinned, reference),
        # Dots after their stems, so they sit on top of them.
        go.Scatter(
            name="dots",
            x=df["year"][~off_scale],
            y=values[~off_scale],
            mode="markers",
            marker=dict(color=EXECUTION_MARK_COLOR, size=11, line=MARK_RING),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
            showlegend=False,
        ),
    ]
    if off_scale.any():
        marks.append(
            _off_scale_trace(
                df["year"][off_scale],
                values[off_scale],
                pinned[off_scale.to_numpy()],
                df["year"].max(),
            )
        )

    shapes, ticks = _zone_shapes_and_ticks(offset)
    shapes.append(
        dict(
            type="line",
            xref="x domain", x0=0, x1=1,
            yref="y", y0=reference, y1=reference,
            # Everything here is measured against this line, so it is dark and
            # heavy — dotted rather than solid, to read as a reference, not data.
            line=dict(color=PEFA_REFERENCE_COLOR, width=2.5, dash="dot"),
        )
    )
    fig = go.Figure(
        data=marks,
        layout=dict(
            title=t("chart.budget_execution", lang),
            plot_bgcolor="white",
            # No legend: the right-hand axis names the zones where they are.
            showlegend=False,
            shapes=shapes,
            xaxis=dict(tickformat="d"),
            yaxis=dict(
                title_text=axis,
                ticksuffix="%",
                fixedrange=True,
                range=[zone_low - gutter, zone_high + gutter],
            ),
            yaxis2=_rating_axis(ticks, lang),
            hovermode="x unified",
        ),
    )
    return apply_locale(fig, lang)


# Execution keeps "Goods and services" separate from the composition chart's
# 3-way split — PERs (e.g. the World Bank's education-spending blog) flag it
# as its own signal of delivery reliability, distinct from wage bill or capital.
EXEC_GOODS_SERVICES = "Goods and services"
EXEC_OTHER = "Other recurrent"
_EXEC_ECON_ORDER = (OP_WAGE_BILL, CAPEX, EXEC_GOODS_SERVICES, EXEC_OTHER)
_EXEC_ECON_BUCKET_MAP = {
    "Wage bill": OP_WAGE_BILL,
    "Capital expenditures": CAPEX,
    "Goods and services": EXEC_GOODS_SERVICES,
}
# Wage bill / capital match the composition chart's colors exactly (its pivot
# table's alphabetical order puts them on QUALITATIVE[0] and [2]). "Other
# recurrent" isn't "Non-wage recurrent" (it excludes goods and services), so
# it doesn't reuse that color — a neutral tone instead; goods and services
# gets an unused palette color.
OTHER_RECURRENT_COLOR = "#B8A99A"  # warm taupe
_EXEC_ECON_COLOR = {
    CAPEX: QUALITATIVE[0],  # light blue
    EXEC_OTHER: OTHER_RECURRENT_COLOR,
    OP_WAGE_BILL: QUALITATIVE[2],  # light green
    EXEC_GOODS_SERVICES: QUALITATIVE[6],  # light orange
}


def _prepare_econ_execution_df(country, sector):
    """Execution rate/variance by economic-category bucket, for one sector.

    ``real_budget`` in the raw table does not remove this prep step: execution
    rates use ``expenditure / budget`` and are unchanged by a common deflator.
    The key work here is collapsing many raw econ labels into the 4 displayed
    buckets and re-aggregating totals per (year, bucket).
    """
    df = server_store.get("func_econ_raw")
    df = filter_country_sort_year(df[df["func"] == sector], country)
    if df.empty:
        return df
    df = df.assign(econ=df["econ"].map(_EXEC_ECON_BUCKET_MAP).fillna(EXEC_OTHER))
    grouped = df.groupby(["year", "econ"], as_index=False).agg(
        budget=("budget", "sum"), expenditure=("expenditure", "sum")
    )
    result = _add_execution_columns(grouped)
    return result if result.empty else result.sort_values(["year", "econ"])


def render_econ_execution_figure(country, lang="en", metric="execution_rate", sector=None):
    if not sector:
        return empty_plot(t("error.data_unavailable", lang))
    econ_df = _prepare_econ_execution_df(country, sector)
    if econ_df.empty:
        return empty_plot(t("error.data_unavailable", lang))
    return create_econ_execution_figure(econ_df, lang=lang, metric=metric)


def create_econ_execution_figure(df, lang="en", metric="execution_rate"):
    """One line per economic-category bucket; ``metric`` selects rate or variance."""
    col, offset, axis = _metric_fields(metric, lang)
    reference = 100 - offset

    fig = go.Figure()
    for bucket in _EXEC_ECON_ORDER:
        bucket_df = df[df["econ"] == bucket]
        if bucket_df.empty:
            continue
        name = translate_econ(bucket, lang)
        fig.add_trace(
            go.Scatter(
                x=bucket_df["year"],
                y=bucket_df[col],
                mode="lines+markers",
                name=name,
                line_color=_EXEC_ECON_COLOR[bucket],
                hovertemplate="<b>" + name + "</b>: %{y:.1f}%<extra></extra>",
            )
        )
    fig.add_hline(y=reference, line_dash="dash", line_color=REFERENCE_LINE_COLOR)
    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(title_text=axis, ticksuffix="%", fixedrange=True)
    fig.update_layout(
        title=t("chart.budget_execution_by_category", lang),
        plot_bgcolor="white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="center", x=0.5),
        margin=dict(b=60),
    )
    return apply_locale(fig, lang)


def _format_econ_execution_clause(df, sector, lang="en"):
    """Highest/lowest-executing category, appended to the execution narrative
    rather than a separate paragraph. Same recent window as the trend clause.

    ``df`` has one row per (year, category), so ``.tail()`` would cut off
    mid-year — filter by year value instead.
    """
    recent_years = sorted(df["year"].unique())[-RECENT_YEARS:]
    recent = df[df["year"].isin(recent_years)]
    means = recent.dropna(subset=["execution_rate"]).groupby("econ")["execution_rate"].mean()
    if len(means) < 2:
        return ""
    high_bucket, low_bucket = means.idxmax(), means.idxmin()

    def label(bucket):
        name = translate_econ(bucket, lang)
        return name[0].lower() + name[1:]

    return t(
        "narrative.econ_execution_breakdown", lang,
        budget=_budget_label(sector, lang),
        high=label(high_bucket), high_rate=means[high_bucket],
        low=label(low_bucket), low_rate=means[low_bucket],
    )


# Recent moves smaller than this read as flat rather than a rise or fall.
STEADY_MARGIN = 2
# "Recent" window length, shared by the trend clause and the by-category
# high/low clause so both describe the same years.
RECENT_YEARS = 5


def format_execution_narrative(df, country, lang="en", sector=None):
    country_label = t(f"country.{country}", lang)
    budget = _budget_label(sector, lang)
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
    lead = t(key, lang, country=country_label, mean=mean_rate, gap=gap, budget=budget)
    lead = lead[0].upper() + lead[1:]

    recent = plot_df.tail(RECENT_YEARS)
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
