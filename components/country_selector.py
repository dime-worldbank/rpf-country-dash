import dash_bootstrap_components as dbc
from dash import html

HIDDEN = {"display": "none"}


def country_selector(countries):
    """Sidebar country dropdown, the label that replaces it, and the separator below.

    With exactly one configured country there is nothing to choose: the country
    name is shown as plain text, so it reads as fixed rather than clickable. The
    dropdown stays in the layout, hidden, since callbacks read its value.
    """
    single = len(countries) == 1
    return [
        dbc.Select(id="country-select", size="sm", **({"style": HIDDEN} if single else {})),
        html.Div(id="country-label", className="country-label", style={} if single else HIDDEN),
        html.Hr(),
    ]


def selector_styles(configured, available):
    """(dropdown style, label style) once the data has loaded: the label for a single
    configured country present in the data; otherwise the dropdown, so that the
    no-data message, shown as its only option, can be read."""
    if len(configured) == 1 and configured[0] in (available or []):
        return HIDDEN, {}
    return {}, HIDDEN
