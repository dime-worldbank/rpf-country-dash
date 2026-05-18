"""Reusable sentence templates for narrative builders.

Structural glue for common narrative shapes — period sentences, extrema
joins, year-range framing. Feature-specific vocabulary (metric names,
extrema labels, value descriptions) is passed in by the caller, so any
feature can reuse these without inheriting another feature's prose.
"""

from utils import format_currency


def year_range_phrase(year_min, year_max):
    """``'in 2020'`` for a single year, ``'from 2018 to 2023'`` otherwise."""
    if year_min == year_max:
        return f"in {year_min}"
    return f"from {year_min} to {year_max}"


def extrema_phrase(extrema, currency_code, low_label, high_label):
    """Join low/high extrema chronologically.

    ``extrema`` is ``{"min": {"year", "value"}, "max": {"year", "value"}}``.
    ``low_label`` / ``high_label`` are noun phrases supplied by the caller
    (e.g. ``"the largest deficit"`` / ``"the largest surplus"``, or
    ``"the lowest"`` / ``"the peak"``).

    A side is dropped when its value is on the wrong side of zero — a "min"
    that's positive isn't a low; a "max" that's negative isn't a high.
    """
    if not extrema:
        return ""

    notes = []
    min_e = extrema.get("min")
    if min_e and min_e["value"] < 0:
        notes.append((
            min_e["year"],
            f"{low_label} of {format_currency(abs(min_e['value']), currency_code)} "
            f"in {min_e['year']}",
        ))
    max_e = extrema.get("max")
    if max_e and max_e["value"] > 0:
        notes.append((
            max_e["year"],
            f"{high_label} of {format_currency(max_e['value'], currency_code)} "
            f"in {max_e['year']}",
        ))

    notes.sort(key=lambda n: n[0])
    phrases = [n[1] for n in notes]
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    return f"{phrases[0]} and {phrases[1]}"


def period_narrative(prefix, metric, start_year, end_year, slope, extras_clause="", forecast=False):
    """Compose ``'{prefix}, between Y1 and Y2, {metric} {verb}, with {extras_clause}.'``.

    Takes primitive trend parameters rather than a segments list so this
    module stays decoupled from any specific trend-detection package.

    Verbs are value-laden (``improved`` / ``deteriorated`` / ``flat``), so
    this fits metrics where direction carries a quality interpretation
    (balance, literacy rate, life expectancy, etc.). For neutral metrics
    consider a sibling helper.
    """
    start_year = int(start_year)
    end_year = int(end_year)

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

    trend = f"between {start_year} and {end_year}, {metric} {verb}"
    body = f"{trend}, with {extras_clause}" if extras_clause else trend
    return f"{prefix}, {body}."


def national_narrative(source_name, metric, avg_clause, year_min, year_max):
    """Build ``'The recent official reports from {source_name} indicate that {metric} {avg_clause} {year_range}.'``.

    ``avg_clause`` is a verb phrase built by the caller from sign / magnitude
    (e.g. ``"averaged a deficit of $1.2B"``).
    """
    return (
        f"The recent official reports from {source_name} indicate "
        f"that {metric} {avg_clause} {year_range_phrase(year_min, year_max)}."
    )
