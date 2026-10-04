"""Spending narrative shared by the Education and Health pages."""
import numpy as np
import pandas as pd
from trend_narrative import InsightExtractor
from trend_narrative_i18n import get_segment_narrative_i18n

from translations import genitive, t
from utils import filter_country_sort_year, get_percentage_change_text


def _growth_rate(start, end):
    """Relative change from start to end; None when either value is missing
    or infinite, or the start is zero."""
    if not (np.isfinite(start) and np.isfinite(end)) or start == 0:
        return None
    return (end - start) / start


def _real_start_end(spending, column, start_year, end_year):
    """Inflation-adjusted value of a nominal spending column in the first
    and the last year."""
    real = spending.real_expenditure / spending.expenditure * spending[column]
    return (
        real[spending.year == start_year].values[0],
        real[spending.year == end_year].values[0],
    )


def sector_spending_narrative(spending, country, sector_key, lang="en"):
    """Narrative for a sector's public spending: the inflation-adjusted
    trend, the central and subnational change between the first and last
    year, and the share of spending decentralized in the last year."""
    spending = filter_country_sort_year(spending, country)

    plot_df = (
        spending.dropna(subset=["real_expenditure"])
        .groupby("year")["real_expenditure"].sum()
        .reset_index()
        .sort_values("year")
    )
    extractor = InsightExtractor(plot_df["year"].values, plot_df["real_expenditure"].values)
    trend_narrative = get_segment_narrative_i18n(
        extractor=extractor,
        metric=t("metric.real_expenditure", lang, meta=True),
        lang=lang,
    )

    if trend_narrative:
        trend_narrative = trend_narrative[0].lower() + trend_narrative[1:]
        text = t("narrative.after_inflation", lang, trend_narrative=trend_narrative)
    else:
        text = ""

    spending = spending.dropna(subset=["real_expenditure", "central_expenditure"])
    if spending.empty:
        return text.rstrip()
    start_year = spending.year.min()
    end_year = spending.year.max()

    central_growth = _growth_rate(
        *_real_start_end(spending, "central_expenditure", start_year, end_year)
    )
    # The subnational sentence continues the central one: both are left out
    # when the central change cannot be computed.
    if central_growth is not None:
        text += t("narrative.central_spending_change", lang, change_text=get_percentage_change_text(central_growth, lang=lang))
        # A country with no subnational tracking at all sums to 0.0 rather
        # than NaN in the func aggregation, so a 0 start means "not tracked",
        # not a real zero.
        subnational_growth = _growth_rate(
            *_real_start_end(spending, "decentralized_expenditure", start_year, end_year)
        )
        if subnational_growth is not None:
            text += t("narrative.subnational_spending_change", lang, change_text=get_percentage_change_text(subnational_growth, lang=lang))
        else:
            # The unavailable message opens with its own full stop.
            text = text.rstrip() + t("narrative.subnational_unavailable", lang)

    decentralization = spending[
        spending.year == end_year
    ].expenditure_decentralization.values[0]
    sector_name = t(sector_key, lang)
    sector_gen = genitive(lang, t(sector_key, lang, meta=True))
    if pd.isna(decentralization) or decentralization == 0:
        text += t(
            "narrative.decentralization_unknown", lang,
            sector=sector_name, sector_gen=sector_gen,
        )
    else:
        text += t(
            "narrative.decentralization_by_year", lang,
            year=end_year, pct=f"{decentralization:.1%}",
            sector=sector_name, sector_gen=sector_gen,
        )

    return text
