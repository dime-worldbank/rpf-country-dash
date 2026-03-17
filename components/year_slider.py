from dash import dcc, html


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


def get_slider_config(expenditure_years, outcome_years):
    """
    Helper function to create the slider configuration.

    @param expenditure_years: list of years from the expenditure dataset
    @param outcome_years: list of years from the outcome dataset
    @return: tuple with (style, marks, selected_year, min_year, max_year, tooltip)
    """
    expenditure_years.sort()
    outcome_years.sort()

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
            {"template": "data not available", "always_visible": True},
        )

    common_years = [year for year in expenditure_years if year in outcome_years]
    min_year, max_year = expenditure_years[0], expenditure_years[-1]

    marks = {}
    for year in expenditure_years:
        if year in common_years:
            marks[str(year)] = {"label": str(year), "style": YEAR_COMPLETE_STYLE}
        else:
            marks[str(year)] = {"label": str(year), "style": YEAR_PARTIAL_STYLE}

    selected_year = max(common_years) if common_years else max_year
    return (
        {"display": "block"},
        marks,
        selected_year,
        min_year,
        max_year,
        {},
    )
