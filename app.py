import dash_bootstrap_components as dbc
import diskcache
import pandas as pd
import json
import os

from dash import dcc, html, Dash, Input, Output, State, page_container, page_registry, no_update
from dash.long_callback import DiskcacheLongCallbackManager
from flask_login import logout_user, current_user
from auth import AUTH_ENABLED
from queries import QueryService
from server import server
from utils import get_login_path, get_prefixed_path

cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.QUARTZ, dbc_css],
    long_callback_manager=long_callback_manager,
    suppress_callback_exceptions=True,
    use_pages=True,
)

HEADER_STYLE = {
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "end",
    "marginTop": "2rem",
    "marginRight": "4rem",
    "fontSize": "20px",
}


SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 10,
    "left": 0,
    "bottom": 0,
    "width": "14rem",
    "padding": "2rem 1rem",
}

CONTENT_STYLE = {
    "marginLeft": "14rem",
    "marginRight": "2rem",
    "padding": "2rem 1rem",
}

db = QueryService.get_instance()

header = html.Div(
    [
        html.Div(id="user-status-header", children=[
            html.A(
                children="logout",
                n_clicks=0,
                id="logout-button",
                style={"display": "none"}
            )
        ])
    ],
    style=HEADER_STYLE
)

def get_relative_path(page_name):
    return page_registry[f"pages.{page_name}"]["relative_path"]

sidebar = html.Div(
    [
        dbc.Row(
            [
                html.Img(
                    src=app.get_asset_url("rpf_logo.png"), style={"height": "100"}
                )
            ]
        ),
        html.Hr(),
        dbc.Select(
            id="country-select",
            size="sm",
        ),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink("Overview", href=get_relative_path("home"), active="exact"),
                dbc.NavLink(
                    "Education", href=get_relative_path("education"), active="exact"
                ),
                dbc.NavLink("Health", href=get_relative_path("health"), active="exact"),
                dbc.NavLink("About", href=get_relative_path("about"), active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(page_container, id="page-content", style=CONTENT_STYLE)

dummy_div = html.Div(id="div-for-redirect")

def layout():
    html_contents = [
        dcc.Location(id="url", refresh=False),
        header,
        sidebar,
        content,
        dummy_div
    ]

    if not AUTH_ENABLED or current_user.is_authenticated:
        html_contents.extend([
            dcc.Store(id="stored-data"),
            dcc.Store(id="stored-basic-country-data"),
            dcc.Store(id="stored-data-subnational"),
            dcc.Store(id="stored-data-func-econ"),
        ])

    return (
        html.Div(
            html_contents
        )
    )


app.layout = layout

@app.callback(
    [Output("url", "pathname"), Output("page-content", "children")],
    [Input("url", "pathname"), Input("logout-button", "n_clicks")]
)
def display_page_or_redirect(pathname, logout_clicks):
    login_path = get_login_path()
    if logout_clicks:
        logout_user()
        return login_path, page_container

    if not AUTH_ENABLED or current_user.is_authenticated:
        if (
            pathname == get_login_path() or
            pathname is None or
            pathname == os.getenv("DEFAULT_ROOT_PATH", "/")
        ):
            return get_prefixed_path("home"), page_container
        return pathname, page_container
    else:
        if pathname != login_path:
            return login_path, page_container
        return pathname, page_container


@app.callback(
    Output("logout-button", "style"),
    Input("url", "pathname")
)
def update_logout_button_visibility(pathname):
    if AUTH_ENABLED and current_user.is_authenticated:
        return {"display": "block", "text-decoration": "underline", "cursor": "pointer"}
    else:
        return {"display": "none"}


@app.callback(Output("stored-data", "data"), Input("stored-data", "data"))
def fetch_data_once(data):
    if data is None:
        df = db.get_expenditure_w_poverty_by_country_year()
        countries = sorted(df["country_name"].unique())
        return {
            "countries": countries,
            "expenditure_w_poverty_by_country_year": df.to_dict("records"),
        }
    return no_update


@app.callback(Output("stored-data-func-econ", "data"), Input("stored-data-func-econ", "data"))
def fetch_func_data_once(data):
    if data is None:
        func_econ_df = db.get_expenditure_by_country_func_econ_year()

        agg_dict = {
            "expenditure": "sum",
            "real_expenditure": "sum",
            "decentralized_expenditure": "sum",
            "central_expenditure": "sum",
            "per_capita_expenditure": "sum",
            "per_capita_real_expenditure": "sum",
        }

        func_df = (
            func_econ_df
            .groupby(["country_name", "year", "func"], as_index=False)
            .agg(agg_dict)
        )
        func_df["expenditure_decentralization"] = func_df["decentralized_expenditure"] / func_df["expenditure"]

        econ_df = (
            func_econ_df
            .groupby(["country_name", "year", "econ"], as_index=False)
            .agg(agg_dict)
        )
        econ_df["expenditure_decentralization"] = econ_df["decentralized_expenditure"] / econ_df["expenditure"]

        return {
            "expenditure_by_country_func_econ_year": func_econ_df.to_dict("records"),
            "expenditure_by_country_func_year": func_df.to_dict("records"),
            "expenditure_by_country_econ_year": econ_df.to_dict("records"),
        }
    return no_update



@app.callback(
    Output("stored-data-subnational", "data"),
    Input("stored-data-subnational", "data"),
    Input("stored-data", "data"),
)
def fetch_subnational_data_once(data, country_data):
    if data is None:
        countries = country_data["countries"]
        df = db.get_adm_boundaries(countries)

        boundaries_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "properties": {"country": x[0], "region": x[1]},
                    "geometry": json.loads(x[2]),
                }
                for x in zip(df.country_name, df.admin1_region, df.boundary)
            ],
        }

        subnational_poverty_df = db.get_subnational_poverty_index(countries)
        geo1_year_df = db.get_expenditure_by_country_geo1_year()
        return {
            "subnational_poverty_index": subnational_poverty_df.to_dict("records"),
            "boundaries": boundaries_geojson,
            "expenditure_by_country_geo1_year": geo1_year_df.to_dict("records"),
        }
    return no_update


@app.callback(
    Output("country-select", "options"),
    Output("country-select", "value"),
    Input("stored-data", "data"),
)
def display_data(data):
    def get_country_select_options(countries):
        options = list({"label": c, "value": c} for c in countries)
        options[0]["selected"] = True
        return options

    if data is not None:
        countries = data["countries"]
        return get_country_select_options(countries), countries[0]
    return ["No data available"], ""


@app.callback(
    Output("stored-basic-country-data", "data"),
    Input("country-select", "options"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
)
def fetch_country_data_once(countries, subnational_data, country_data):
    if country_data is None:
        countries = [x["label"] for x in countries]
        country_df = db.get_basic_country_data(countries)
        country_info = country_df.set_index("country_name").T.to_dict()

        expenditure_df = pd.DataFrame(
            subnational_data["expenditure_by_country_geo1_year"],
            columns=["country_name", "year"],
        )
        poverty_df = pd.DataFrame(
            subnational_data["subnational_poverty_index"],
            columns=["country_name", "year", "poor215"],
        )

        expenditure_years = (
            expenditure_df.groupby("country_name")["year"]
            .apply(lambda x: sorted(x.unique()))
            .to_dict()
        )
        poverty_years = (
            poverty_df.groupby("country_name")["year"]
            .apply(lambda x: sorted(x.unique()))
            .to_dict()
        )

        poverty_level_stats = (
            pd.merge(country_df, poverty_df, on="country_name")
            .groupby("income_level")["poor215"]
            .agg(["min", "max"])
            .reset_index()
        )
        poverty_level_stats = (
            poverty_level_stats.set_index("income_level").apply(tuple, axis=1).to_dict()
        )

        for country, years in expenditure_years.items():
            country_info[country]["expenditure_years"] = years

        for country, years in poverty_years.items():
            country_info[country]["poverty_years"] = years

        for country, info in country_info.items():

            country_income_level = info["income_level"]
            info["poverty_bounds"] = poverty_level_stats[country_income_level]

        return {"basic_country_info": country_info}
    return no_update



if __name__ == "__main__":
    app.run_server(debug=True)
