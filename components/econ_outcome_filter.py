"""Reusable "economic category + service-delivery indicator" filter bar.

Two labeled dropdowns: economic category (options populated per country from a
data store) and service-delivery indicator (a fixed list the caller supplies).
Selecting a category sets the indicator to its natural default; the reverse is
deliberately not wired.
"""
import urllib.parse

import dash_bootstrap_components as dbc
from dash import html

import server_store
from constants import translate_econ
from translations import t

ALL_ECON = "__all__"


# ---------------------------------------------------------------------------
# Filter icon — inline funnel as a data URI (no icon font is loaded).
# ---------------------------------------------------------------------------
_FILTER_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' "
    "fill='#495057' viewBox='0 0 16 16'>"
    "<path d='M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334"
    "L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 "
    "3.834A.5.5 0 0 1 1.5 3.5z'/></svg>"
)
_FILTER_ICON = "data:image/svg+xml," + urllib.parse.quote(_FILTER_SVG)


def _filter_item(label_key, select_id, value, options, lang):
    """One labeled dropdown (icon + label on top of the select)."""
    return html.Div(
        [
            html.Div(
                [
                    html.Img(src=_FILTER_ICON, className="edu-filter-icon", alt=""),
                    dbc.Label(
                        t(label_key, lang),
                        html_for=select_id,
                        className="edu-filter-label mb-0",
                    ),
                ],
                className="edu-filter-label-row",
            ),
            dbc.Select(
                id=select_id,
                size="sm",
                className="econ-filter-select",
                value=value,
                options=options,
            ),
        ],
        className="edu-filter-item",
    )


def filter_bar(econ_id, outcome_id, outcome_options, outcome_value, lang="en"):
    """The two-dropdown filter bar (economic category + indicator).

    ``outcome_options`` is a list of ``{"label", "value"}`` dicts; the economic
    category options are populated per country by :func:`econ_options` via the
    page callback.
    """
    lang = lang or "en"
    return html.Div(
        [
            _filter_item(
                "label.economic_category",
                econ_id,
                ALL_ECON,
                [{"label": t("dropdown.all_econ_categories", lang), "value": ALL_ECON}],
                lang,
            ),
            _filter_item(
                "label.outcome_indicator",
                outcome_id,
                outcome_value,
                outcome_options,
                lang,
            ),
        ],
        className="edu-filter-bar",
    )


def econ_options(store_key, country, lang, current_value):
    """(options, value) for the economic-category dropdown, per country.

    ``store_key`` is the server_store key of a frame with ``country_name`` and
    ``econ`` columns. Keeps the current selection if still valid, else "All".
    """
    lang = lang or "en"
    options = [{"label": t("dropdown.all_econ_categories", lang), "value": ALL_ECON}]
    if country:
        df = server_store.get(store_key)
        econ_values = sorted(
            df[df["country_name"] == country]["econ"].dropna().unique()
        )
        options += [
            {"label": translate_econ(e, lang), "value": e} for e in econ_values
        ]
    valid_values = {opt["value"] for opt in options}
    value = current_value if current_value in valid_values else ALL_ECON
    return options, value
