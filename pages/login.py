import dash
import dash_bootstrap_components as dbc
from auth import authenticate
from dash import html, dcc, callback, Output, Input, State

dash.register_page(__name__)

def layout(**kwargs):
    return dbc.Container(
        [
            dbc.Row([
                dbc.Col([html.Div('')], width=3),
                dbc.Col(
                    dbc.Form([
                            dbc.Label("Username", html_for="username", className="mb-1"),
                            dbc.Input(
                                type="text",
                                id="username",
                                placeholder="Enter your username",
                                className="mb-3",
                            ),
                            dbc.Label("Password", html_for="password", className="mb-1"),
                            dbc.Input(
                                type="password",
                                id="password",
                                placeholder="Enter your password",
                                className="mb-3",
                            ),
                            dbc.Button(
                                "Login", color="primary", id="login-button", n_clicks=0, className="w-100 mb-3"
                            ),
                            html.Div(id="login-alert"),
                    ]),
                    width=6,
                ),
                dbc.Col([html.Div('')], width=3),
            ]),
            html.Div(id="hidden_div_for_redirect_callback"),
        ],
        className="mt-5",
    )

@callback(
    Output("login-alert", "children"),
    Output("hidden_div_for_redirect_callback", "children"),
    Input("login-button", "n_clicks"),
    State("username", "value"),
    State("password", "value"),
)
def login_button_click(n_clicks, username, password):
    if n_clicks > 0:
        if authenticate(username, password):
            return "", dcc.Location(pathname=dash.get_relative_path("/home"), id="home")
        else:
            return dbc.Alert("Invalid credentials", color="danger", dismissable=True), dash.no_update
    return dash.no_update, dash.no_update

