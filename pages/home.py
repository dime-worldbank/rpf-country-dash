import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from utils import (
    add_currency_column,
    filter_country_sort_year,
    empty_plot,
    require_login,
)
from components.source_metadata_popover import chart_container
from queries import QueryService
import server_store


db = QueryService.get_instance()

dash.register_page(__name__)


WEO_SOURCE = "WEO (World Economic Outlook), IMF — General Government"
GFS_SOO_SOURCE = "GFS_SOO (Statement of Operations), IMF — Budgetary Central Government"


@require_login
def layout():
    return html.Div(
        children=[
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Row(
                            dbc.Col(
                                html.H3(children="Revenue & Expenditure")
                            )
                        ),
                        dbc.Row(
                            dbc.Col(
                                chart_container("revenue-expenditure-deficit"),
                                xs={"size": 12, "offset": 0},
                                sm={"size": 12, "offset": 0},
                                md={"size": 12, "offset": 0},
                                lg={"size": 12, "offset": 0},
                            )
                        ),
                        dbc.Row(
                            dbc.Col(
                                chart_container("revenue-expenditure-deficit-weo"),
                                xs={"size": 12, "offset": 0},
                                sm={"size": 12, "offset": 0},
                                md={"size": 12, "offset": 0},
                                lg={"size": 12, "offset": 0},
                            )
                        ),
                        dbc.Row(
                            dbc.Col(
                                chart_container("revenue-expenditure-deficit-gfs"),
                                xs={"size": 12, "offset": 0},
                                sm={"size": 12, "offset": 0},
                                md={"size": 12, "offset": 0},
                                lg={"size": 12, "offset": 0},
                            )
                        ),
                    ]
                )
            ),
            dcc.Store(id="stored-data-revenue-budget"),
            dcc.Store(id="stored-data-government-budget"),
        ]
    )


@callback(
    Output("stored-data-revenue-budget", "data"),
    Input("stored-data-revenue-budget", "data"),
    Input("stored-data", "data"),
)
def fetch_revenue_budget_data_once(revenue_data, shared_data):
    if revenue_data is None and shared_data:
        server_store.get("revenue_budget")
        return {"ready": True}
    return dash.no_update


@callback(
    Output("stored-data-government-budget", "data"),
    Input("stored-data-government-budget", "data"),
    Input("stored-data", "data"),
)
def fetch_government_budget_data_once(gov_data, shared_data):
    if gov_data is None and shared_data:
        server_store.get("government_budget")
        return {"ready": True}
    return dash.no_update


def revenue_expenditure_deficit_figure(df, currency_code, title="Revenue, Expenditure, and Surplus / Deficit over time"):
    if df.empty:
        return empty_plot("No revenue budget data available")

    df = df.copy().sort_values("year")
    df = df[df["year"] <= 2025]

    if df.empty:
        return empty_plot("No revenue budget data available")

    df['deficit'] = df['revenue'] - df['expenditure']
    add_currency_column(df, 'revenue', currency_code)
    add_currency_column(df, 'expenditure', currency_code)
    add_currency_column(df, 'deficit', currency_code)

    fig = go.Figure()

    colors = ['green' if x >= 0 else 'red' for x in df['deficit']]

    fig.add_trace(
        go.Bar(
            name="Surplus / Deficit",
            x=df.year,
            y=df.deficit,
            marker_color=colors,
            opacity=0.5,
            customdata=df['deficit_formatted'],
            hovertemplate="<b>Surplus / Deficit</b>: %{customdata}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            name="Revenue",
            x=df.year,
            y=df.revenue,
            mode="lines+markers",
            marker_color="darkgreen",
            customdata=df['revenue_formatted'],
            hovertemplate="<b>Revenue</b>: %{customdata}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            name="Expenditure",
            x=df.year,
            y=df.expenditure,
            mode="lines+markers",
            marker_color="darkblue",
            customdata=df['expenditure_formatted'],
            hovertemplate="<b>Expenditure</b>: %{customdata}<extra></extra>",
        )
    )

    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color="black",
        line_width=1,
    )

    fig.update_xaxes(
        range=[2009.5, 2025.5],
        tickmode="array",
        tickvals=list(range(2010, 2026)),
        tickformat="d",
        zeroline=False,
    )
    fig.update_yaxes(
        zeroline=True,
        zerolinecolor="black",
        zerolinewidth=1,
    )
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1),
    )

    return fig


@callback(
    Output("revenue-expenditure-deficit", "figure"),
    Input("stored-data-revenue-budget", "data"),
    Input("country-select", "value"),
    Input("stored-basic-country-data", "data"),
)
def render_revenue_budget_figure(revenue_data, country, country_data):
    if not revenue_data or not country_data or not country:
        return dash.no_update

    all_data = server_store.get("revenue_budget")
    df = filter_country_sort_year(all_data, country)

    if df.empty:
        return empty_plot("No revenue budget data available")

    currency_code = server_store.get("basic_country_info")[country]['currency_code']
    return revenue_expenditure_deficit_figure(
        df, currency_code,
        title="Togo Revenue Budget — Revenue, Expenditure & Surplus / Deficit",
    )


@callback(
    Output("revenue-expenditure-deficit-weo", "figure"),
    Output("revenue-expenditure-deficit-gfs", "figure"),
    Input("stored-data-government-budget", "data"),
    Input("country-select", "value"),
    Input("stored-basic-country-data", "data"),
)
def render_government_budget_figures(gov_data, country, country_data):
    if not gov_data or not country_data or not country:
        return dash.no_update, dash.no_update

    all_data = server_store.get("government_budget")
    df = filter_country_sort_year(all_data, country)

    currency_code = server_store.get("basic_country_info")[country]['currency_code']

    weo_df = df[df["source"] == WEO_SOURCE]
    gfs_df = df[df["source"] == GFS_SOO_SOURCE]

    weo_fig = revenue_expenditure_deficit_figure(
        weo_df, currency_code,
        title="WEO (IMF, General Government) — Revenue, Expenditure & Surplus / Deficit",
    )
    gfs_fig = revenue_expenditure_deficit_figure(
        gfs_df, currency_code,
        title="GFS_SOO (IMF, Budgetary Central Government) — Revenue, Expenditure & Surplus / Deficit",
    )
    return weo_fig, gfs_fig
