import dash
import dash_bootstrap_components as dbc
from auth import authenticate
from dash import html, dcc, callback, Output, Input, State
from translations import t

dash.register_page(__name__)

def layout(**kwargs):
    return dbc.Container(
        [
            dbc.Row([
                dbc.Col([html.Div('')], width=3),
                dbc.Col(
                    dbc.Form(id="login-form"),
                    width=6,
                ),
                dbc.Col([html.Div('')], width=3),
            ]),
            html.Div(id="hidden_div_for_redirect_callback"),
        ],
        className="mt-5",
    )


@callback(
    Output("login-form", "children"),
    Input("stored-language", "data"),
)
def render_login_form(lang):
    lang = lang or "en"
    return [
        dbc.Label(t("login.username", lang), html_for="username", className="mb-1"),
        dbc.Input(
            type="text",
            id="username",
            placeholder=t("login.enter_username", lang),
            className="mb-3",
        ),
        dbc.Label(t("login.password", lang), html_for="password", className="mb-1"),
        dbc.Input(
            type="password",
            id="password",
            placeholder=t("login.enter_password", lang),
            className="mb-3",
        ),
        dbc.Button(
            t("login.button", lang), color="primary", id="login-button", n_clicks=0, className="w-100 mb-3"
        ),
        html.Div(id="login-alert"),
    ]


@callback(
    Output("login-alert", "children"),
    Output("hidden_div_for_redirect_callback", "children"),
    Input("login-button", "n_clicks"),
    State("username", "value"),
    State("password", "value"),
    Input("stored-language", "data"),
)
def login_button_click(n_clicks, username, password, lang):
    lang = lang or "en"
    if n_clicks > 0:
        if authenticate(username, password):
            return "", dcc.Location(pathname=dash.get_relative_path("/home"), id="home")
        else:
            return dbc.Alert(t("login.invalid_credentials", lang), color="danger", dismissable=True), dash.no_update
    return dash.no_update, dash.no_update
