"""Narrative builders for the revenue-expenditure chart.

All functions take plain Python values (numbers, dicts, lists) as input,
not DataFrames. Insights (segment lists, extrema, mean balance) may come
from the trend_narrative package or from custom computation — this module
only formats them into prose.
"""

from utils import format_currency


def extrema_phrase(extrema, currency_code, forecast=False):
    """Chronologically-ordered phrase joining the largest surplus/deficit.

    Args:
        extrema: dict ``{"min": {"year": int, "value": float},
                          "max": {"year": int, "value": float}}``
                 — "min" is the lowest balance (deficit), "max" is the
                 highest (surplus). Either key may be absent or its value
                 may be on the wrong side of zero, in which case it's
                 dropped.
        currency_code: ISO currency string used by :func:`format_currency`.
        forecast: When True, prefixes the labels with "projected".
    """
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


def period_narrative(prefix, segments, extrema, currency_code, forecast=False):
    """Compose a ``'{prefix}, [trend], with [extrema].'`` sentence.

    Args:
        prefix: Leading clause like ``"Based on historical GFS data"``.
        segments: List of segment dicts from
            :class:`trend_narrative.InsightExtractor`. Only the first
            segment is used (start_year, end_year, slope).
        extrema: Dict shaped for :func:`extrema_phrase`.
        currency_code: ISO currency string.
        forecast: Future-tense wording when True.

    Returns "" when there are no segments.
    """
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
    extras = extrema_phrase(extrema, currency_code, forecast=forecast)
    body = f"{trend}, with {extras}" if extras else trend
    return f"{prefix}, {body}."


def national_narrative(source_name, year_min, year_max, mean_balance, currency_code):
    """Build the ``'The recent official reports from {source_name} indicate ...'`` sentence.

    Args:
        source_name: Display name of the source (e.g. the data_source field).
        year_min, year_max: Inclusive year range covered by national data.
        mean_balance: Mean of (revenue − expenditure) over the period.
        currency_code: ISO currency string.
    """
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
