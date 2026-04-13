import dash_bootstrap_components as dbc
import pandas as pd
import json
import os


from dash import (
    dcc,
    html,
    Dash,
    Input,
    Output,
    State,
    MATCH,
    ctx,
    page_container,
    page_registry,
    no_update,
    callback_context,
)
from urllib.parse import parse_qs, urlparse

from components.func_operational_vs_capital_spending import prepare_prop_econ_by_func_df
from components.source_metadata_popover import (
    CHART_METADATA,
    build_modal_children,
    build_modal_info,
    get_coverage_years,
)
from flask_login import logout_user, current_user
from auth import AUTH_ENABLED
from queries import QueryService
import server_cache
from server import server
from utils import get_login_path, get_prefixed_path, simplify_geometry
from viz_theme import (
    DEFAULT_THEME, VALID_THEMES, init_plotly_theme,
    SHOW_FOOTER, FOOTER_ACKNOWLEDGMENT_TEXT,
)

app = Dash(
    __name__,
    server=server,
    suppress_callback_exceptions=True,
    use_pages=True,
)

app.index_string = f'''
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
    </head>
    <body class="theme-{DEFAULT_THEME}">
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
'''

init_plotly_theme()

db = QueryService.get_instance()

header = html.Div(
    [
        html.Div(
            id="user-status-header",
            children=[
                html.A(
                    children="logout",
                    n_clicks=0,
                    id="logout-button",
                    style={"display": "none"},
                )
            ],
        )
    ],
    id="header",
)


def get_relative_path(page_name):
    return page_registry[f"pages.{page_name}"]["relative_path"]


sidebar = html.Div(
    [
        dbc.Row(
            [html.Img(src=app.get_asset_url("rpf_logo.png"), alt="Reimagining Public Finance", style={"height": "100"})]
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
                dbc.NavLink("Education", href=get_relative_path("education"), active="exact"),
                dbc.NavLink("Health", href=get_relative_path("health"), active="exact"),
                dbc.NavLink("About", href=get_relative_path("about"), active="exact"),
            ],
            pills=True,
        ),
    ],
    id="sidebar",
)

content = html.Div(page_container, id="page-content")

app_footer = html.Div(
    [
        html.A(
            html.Img(src=app.get_asset_url("wbg_logo_color.svg"), alt="World Bank Group", className="footer-logo"),
            href="https://www.worldbank.org/",
            target="_blank",
        ),
        html.Span(FOOTER_ACKNOWLEDGMENT_TEXT, className="footer-acknowledgment"),
        html.A(
            html.Img(src=app.get_asset_url("FM_umbrella_trust_fund_logo.jpg"), alt="Financial Management Umbrella Trust Fund", className="footer-logo"),
            href="https://www.worldbank.org/en/programs/financial-management-umbrella-program",
            target="_blank",
        ),
        html.A(
            html.Img(src=app.get_asset_url("SDGfund_logo.png"), alt="SDG Trust Fund", className="footer-logo"),
            href="https://www.worldbank.org/en/programs/partnership-fund-for-the-sustainable-development-goals",
            target="_blank",
        ),
    ],
    id="app-footer",
    style={"display": "flex" if SHOW_FOOTER else "none"},
)

dummy_div = html.Div(id="div-for-redirect")


def layout():
    html_contents = [
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="theme-store", data=DEFAULT_THEME),
        dcc.Store(id="default-theme-store", data=DEFAULT_THEME),
        header,
        sidebar,
        content,
        app_footer,
        dummy_div,
    ]

    if not AUTH_ENABLED or (current_user and current_user.is_authenticated):
        html_contents.extend(
            [
                dcc.Store(id="stored-data"),
                dcc.Store(id="stored-basic-country-data"),
                dcc.Store(id="stored-data-subnational"),
                dcc.Store(id="stored-data-func-econ"),
                dcc.Store(id="stored-data-subnat-boundaries"),
                dcc.Store(id="stored-source-metadata"),
            ]
        )

    return html.Div(html_contents, id="app-container")


app.layout = layout


@app.callback(
    [Output("url", "pathname"), Output("page-content", "children")],
    [Input("url", "pathname"), Input("logout-button", "n_clicks")],
)
def display_page_or_redirect(pathname, logout_clicks):
    login_path = get_login_path()
    if logout_clicks:
        logout_user()
        return login_path, page_container

    if not AUTH_ENABLED or current_user.is_authenticated:
        if (
            pathname == get_login_path()
            or pathname is None
            or pathname == os.getenv("DEFAULT_ROOT_PATH", "/")
        ):
            return get_prefixed_path("home"), page_container
        return no_update, page_container
    else:
        if pathname != login_path:
            return login_path, page_container
        return no_update, page_container


@app.callback(Output("logout-button", "style"), Input("url", "pathname"))
def update_logout_button_visibility(pathname):
    if AUTH_ENABLED and current_user.is_authenticated:
        return {"display": "block", "text-decoration": "underline", "cursor": "pointer"}
    else:
        return {"display": "none"}


@app.callback(Output("stored-data", "data"), Input("stored-data", "data"))
def fetch_data_once(data):
    if data is None or not server_cache.has("expenditure_w_poverty"):
        df = db.get_expenditure_w_poverty_by_country_year()
        countries = sorted(df["country_name"].unique())
        server_cache.set("expenditure_w_poverty", df)
        return {"ready": True, "countries": countries}
    return no_update

@app.callback(
    Output("stored-data-func-econ", "data"), Input("stored-data-func-econ", "data")
)
def fetch_func_data_once(data):
    if data is None or not server_cache.has("func_by_country_year"):
        func_econ_df = db.get_expenditure_by_country_func_econ_year()

        agg_dict = {
            "expenditure": "sum",
            "budget": "sum",
            "real_expenditure": "sum",
            "domestic_funded_budget": "sum",
            "decentralized_expenditure": "sum",
            "central_expenditure": "sum",
            "per_capita_expenditure": "sum",
            "per_capita_real_expenditure": "sum",
        }

        func_df = func_econ_df.groupby(
            ["country_name", "year", "func"], as_index=False
        ).agg(agg_dict)
        func_df["expenditure_decentralization"] = (
            func_df["decentralized_expenditure"] / func_df["expenditure"]
        )
        func_df["real_domestic_funded_budget"] = (
            func_df["real_expenditure"] / func_df["expenditure"]
        ) * func_df["domestic_funded_budget"]
        econ_df = func_econ_df.groupby(
            ["country_name", "year", "econ"], as_index=False
        ).agg(agg_dict)
        econ_df["expenditure_decentralization"] = (
            econ_df["decentralized_expenditure"] / econ_df["expenditure"]
        )
        prop_econ_by_func_df = prepare_prop_econ_by_func_df(func_econ_df, agg_dict)

        server_cache.set("func_econ_raw", func_econ_df)
        server_cache.set("func_by_country_year", func_df)
        server_cache.set("econ_by_country_year", econ_df)
        server_cache.set("prop_econ_by_func", prop_econ_by_func_df)
        return {"ready": True}
    return no_update


@app.callback(
    Output("stored-data-subnational", "data"),
    Input("stored-data-subnational", "data"),
    Input("stored-data", "data"),
)
def fetch_subnational_data_once(data, country_data):
    if (data is None or not server_cache.has("disputed_boundaries")) and country_data:
        countries = country_data["countries"]
        df_disputed = db.get_disputed_boundaries(countries)

        disputed_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "properties": {"country": x[0], "region": x[2]},
                    "geometry": simplify_geometry(json.loads(x[1])),
                }
                for x in zip(df_disputed.country_name, df_disputed.boundary, df_disputed.region_name)
            ],
        }

        poverty_df = db.get_subnational_poverty_rate(countries)
        geo1_df = db.get_expenditure_by_country_geo1_year()
        geo1_func_df = db.expenditure_and_outcome_by_country_geo1_func_year()
        geo0_sub_func_df = db.get_expenditure_by_country_sub_func_year()

        server_cache.set("subnational_poverty_rate", poverty_df)
        server_cache.set("disputed_boundaries", disputed_geojson)
        server_cache.set("geo1_expenditure", geo1_df)
        server_cache.set("geo1_func_expenditure", geo1_func_df)
        server_cache.set("sub_func_expenditure", geo0_sub_func_df)
        return {"ready": True}
    return no_update


@app.callback(
    Output("country-select", "options"),
    Output("country-select", "value"),
    Input("stored-data", "data"),
    Input("url", "search"),
    State("country-select", "value"),
)
def display_data(data, search, current_country):
    """
    Populate country dropdown and optionally select country from URL.
    Usage: ?country=Kenya or ?country=Kenya&theme=wbg
    """
    def get_country_select_options(countries):
        options = list({"label": c, "value": c} for c in countries)
        options[0]["selected"] = True
        return options

    if data is not None:
        countries = data["countries"]
        triggered_id = callback_context.triggered[0]["prop_id"] if callback_context.triggered else ""

        # Only read from URL on initial load (stored-data trigger) or explicit URL change
        if "stored-data" in triggered_id or not current_country:
            selected_country = countries[0]
            if search:
                params = parse_qs(search.lstrip("?"))
                url_country = params.get("country", [None])[0]
                if url_country and url_country in countries:
                    selected_country = url_country
            return get_country_select_options(countries), selected_country

        # URL changed but we already have a country selected - keep current
        return get_country_select_options(countries), current_country
    return ["No data available"], ""


@app.callback(
    Output("stored-basic-country-data", "data"),
    Input("country-select", "options"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
)
def fetch_country_data_once(countries, subnational_data, country_data):
    if (country_data is None or not server_cache.has("basic_country_info")) and countries and subnational_data:
        country_labels = [x["label"] for x in countries]
        country_df = db.get_basic_country_data(country_labels)
        country_info = country_df.set_index("country_name").T.to_dict()

        expenditure_df = server_cache.get("geo1_expenditure")[["country_name", "year"]]
        poverty_df = server_cache.get("subnational_poverty_rate")[["country_name", "year", "poverty_rate"]]

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
            .groupby("income_level")["poverty_rate"]
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

        server_cache.set("basic_country_info", country_info)
        return {"ready": True}
    return no_update


@app.callback(
    Output("stored-data-subnat-boundaries", "data"),
    Input("stored-data-subnat-boundaries", "data"),
    Input("country-select", "value"),
)
def fetch_subnat_boundary_data_once(geo_data, country):
    if not country:
        return no_update

    if geo_data is None:
        data_to_store = {}
    else:
        data_to_store = geo_data

    if data_to_store.get(country):
        return data_to_store

    db = QueryService.get_instance()
    df = db.get_adm_boundaries([country])
    boundaries_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {"country": x[0], "region": x[1]},
                "geometry": simplify_geometry(json.loads(x[2])),
            }
            for x in zip(df.country_name, df.admin1_region, df.boundary)
        ],
    }
    server_cache.set(f"subnat_boundaries:{country}", boundaries_geojson)
    data_to_store[country] = True
    return data_to_store


@app.callback(
    Output("theme-store", "data"),
    Input("url", "search"),
    State("theme-store", "data"),
)
def update_theme_from_url(search, current_theme):
    """
    Parse theme from URL parameter and update theme store.
    Usage: ?theme=wbg or ?theme=quartz
    """
    theme = current_theme or DEFAULT_THEME

    if search:
        params = parse_qs(search.lstrip("?"))
        url_theme = params.get("theme", [None])[0]
        if url_theme and url_theme.lower() in VALID_THEMES:
            theme = url_theme.lower()

    return theme


app.clientside_callback(
    """
    function(theme) {
        document.body.className = 'theme-' + (theme || 'wbg');
        return '';
    }
    """,
    Output("div-for-redirect", "className"),
    Input("theme-store", "data"),
)


app.clientside_callback(
    """
    function(country, pathname, theme, defaultTheme) {
        var params = new URLSearchParams();
        if (country) params.set('country', country);
        if (theme && theme !== defaultTheme) params.set('theme', theme);
        var queryString = params.toString();
        var suffix = queryString ? '?' + queryString : '';

        // Update nav link hrefs
        document.querySelectorAll('#sidebar .nav-link').forEach(function(link) {
            var base = link.getAttribute('href').split('?')[0];
            link.setAttribute('href', base + suffix);
        });

        // Update current URL
        if (country) {
            var url = new URL(window.location);
            url.search = queryString;
            window.history.replaceState({}, '', url);
        }

        return window.dash_clientside.no_update;
    }
    """,
    Output("sidebar", "id"),
    [
        Input("country-select", "value"),
        Input("url", "pathname"),
        Input("theme-store", "data"),
    ],
    State("default-theme-store", "data"),
    prevent_initial_call=True,
)

@app.callback(
    Output("stored-source-metadata", "data"),
    Input("stored-source-metadata", "data"),
)
def fetch_source_metadata_once(data):
    if data is None:
        indicator_df = db.get_indicator_data_availability()
        boost_urls_df = db.get_boost_source_urls()

        # Pre-build source URL maps indexed by country for efficient lookup
        source_urls_by_country = {}

        # Add BOOST URLs
        for _, row in boost_urls_df.iterrows():
            country = row["country_name"]
            if country not in source_urls_by_country:
                source_urls_by_country[country] = {}
            url = row.get("source_url")
            if url:
                source_urls_by_country[country]["boost"] = url

        # Add indicator URLs
        for _, row in indicator_df.iterrows():
            country = row["country_name"]
            if country not in source_urls_by_country:
                source_urls_by_country[country] = {}
            url = row.get("source_url")
            if url:
                key = row["indicator_key"]
                source_urls_by_country[country][key] = url

        return {
            "indicator_availability": indicator_df.to_dict("records"),
            "boost_source_urls": boost_urls_df.to_dict("records"),
            "source_urls_by_country": source_urls_by_country,
        }
    return no_update


@app.callback(
    Output({"type": "source-info-modal", "index": MATCH}, "is_open"),
    Output({"type": "source-info-modal", "index": MATCH}, "children"),
    Input({"type": "source-info-btn", "index": MATCH}, "n_clicks"),
    State("country-select", "value"),
    State("stored-source-metadata", "data"),
    prevent_initial_call=True,
)
def open_source_info_modal(n_clicks, country, source_meta):
    if not n_clicks:
        return no_update, no_update

    index = ctx.triggered_id["index"]
    info = build_modal_info(index, country, source_meta)
    return True, build_modal_children(info)


@app.callback(
    Output({"type": "source-info-modal", "index": MATCH}, "is_open", allow_duplicate=True),
    Input({"type": "source-info-close", "index": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def close_source_info_modal(n_clicks):
    if n_clicks:
        return False
    return no_update


if __name__ == "__main__":
    app.run(debug=True)
