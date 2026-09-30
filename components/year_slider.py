from dash import dcc, html

from constants import START_YEAR
from translations import t


def slider(id, container_id):
    return html.Div(
        id=container_id,
        children=[
            dcc.Slider(
                id=id,
                min=0,
                max=0,
                value=None,
                step=None,
                included=False,
            ),
        ],
    )


YEAR_COMPLETE_STYLE = {"color": "#009FDA", "fontWeight": "700"}
YEAR_PARTIAL_STYLE = {"color": "#888888", "fontWeight": "400"}
YEAR_DEFAULT_STYLE = {"color": "#888888"}


def get_slider_config(expenditure_years, outcome_years, lang="en"):
    """
    Helper function to create the slider configuration.

    @param expenditure_years: list of years from the expenditure dataset
    @param outcome_years: list of years from the outcome dataset
    @return: tuple with (style, marks, selected_year, min_year, max_year, tooltip)
    """
    # Clamp to the display floor so the slider matches the charts (which filter to
    # >= START_YEAR); a raw expenditure year like 2009 would otherwise show here.
    expenditure_years = sorted(y for y in expenditure_years if y >= START_YEAR)
    outcome_years = sorted(y for y in outcome_years if y >= START_YEAR)

    if not expenditure_years:
        marks = {
            2015: {"label": "2015", "style": YEAR_DEFAULT_STYLE},
            2010: {"label": "2010", "style": YEAR_DEFAULT_STYLE},
            2021: {"label": "2021", "style": YEAR_DEFAULT_STYLE},
        }
        return (
            {"opacity": 0.5, "pointer-events": "none"},
            marks,
            2015,
            2010,
            2021,
            {"template": t("error.data_not_available", lang), "always_visible": True},
        )

    # Marks span the union of both datasets: a year present in only one (spending
    # without outcome, or outcome without spending like a later poverty survey)
    # still shows, styled incomplete. Both-present years are styled complete.
    common_years = set(expenditure_years) & set(outcome_years)
    all_years = sorted(set(expenditure_years) | set(outcome_years))

    marks = {}
    for year in all_years:
        style = YEAR_COMPLETE_STYLE if year in common_years else YEAR_PARTIAL_STYLE
        marks[str(year)] = {"label": str(year), "style": style}

    min_year, max_year = all_years[0], all_years[-1]
    selected_year = max(common_years) if common_years else expenditure_years[-1]
    return (
        {"display": "block"},
        marks,
        selected_year,
        min_year,
        max_year,
        {},
    )
