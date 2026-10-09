import dash_bootstrap_components as dbc
from dash import html

HIDDEN = {"display": "none"}


def country_selector(countries):
    """Sidebar country dropdown and the separator below it.

    With exactly one configured country there is nothing to choose: the
    dropdown stays in the layout, since callbacks read its value, but is
    hidden along with its separator.
    """
    if len(countries) == 1:
        return [dbc.Select(id="country-select", size="sm", style=HIDDEN)]
    return [dbc.Select(id="country-select", size="sm"), html.Hr()]


def country_select_style(configured, available):
    """Dropdown style once the data has loaded: hidden for a single
    configured country present in the data, visible otherwise so that the
    no-data message, shown as the dropdown's only option, can be read."""
    return HIDDEN if len(configured) == 1 and configured[0] in (available or []) else {}
