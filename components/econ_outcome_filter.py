"""Reusable "economic category + service-delivery indicator" filter bar.

Two labeled dropdowns: economic category (options populated per country from a
data store) and service-delivery indicator (a fixed list the caller supplies).
Selecting a category sets the indicator to its natural default; the reverse is
deliberately not wired.
"""
import dash_bootstrap_components as dbc
from dash import html

from translations import t

ALL_ECON = "__all__"

def _filter_item(label_key, select_id, value, options, lang):
    """One labeled dropdown (label on top of the select)."""
    return html.Div(
        [
            html.Div(
                [
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
    category options are populated per country by the page callback.
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


