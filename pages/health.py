import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import traceback
from constants import MAP_DISCLAIMER
from queries import QueryService
from utils import (
    empty_plot,
    filter_country_sort_year,
    generate_error_prompt,
    get_correlation_text,
    get_percentage_change_text,
    millify,
    require_login,
)
from components.func_operational_vs_capital_spending import render_econ_breakdown
from components.edu_health_across_space import (
    update_year_slider,
    render_func_subnat_overview,
    update_func_expenditure_map,
    update_hd_index_map,
    render_func_subnat_rank,
)
from components.disclaimer_div import disclaimer_tooltip

db = QueryService.get_instance()

dash.register_page(__name__)


@require_login
def layout():
    return html.Div(
        children=[
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Tabs(
                            id="health-tabs",
                            active_tab="health-tab-time",
                            children=[
                                dbc.Tab(label="Over Time", tab_id="health-tab-time"),
                                dbc.Tab(
                                    label="Across Space", tab_id="health-tab-space"
                                ),
                            ],
                            style={"marginBottom": "2rem"},
                        ),
                        html.Div(id="health-content"),
                    ]
                )
            ),
            dcc.Store(id="stored-data-health-total"),
            dcc.Store(id="stored-data-health-outcome"),
            dcc.Store(id="stored-data-health-private"),
            dcc.Store(id="stored-data-health-sub-func"),
        ]
    )

@callback(
    Output("stored-data-health-total", "data"),
    Input("stored-data-health-total", "data"),
    Input("stored-data-func-econ", "data"),
)
def fetch_health_total_data_once(health_data, shared_data):
    if health_data is None:
        # filter shared data down to health specific
        exp_by_func = pd.DataFrame(shared_data["expenditure_by_country_func_year"])
        pub_exp = exp_by_func[exp_by_func.func == "Health"]

        return {
            "health_public_expenditure": pub_exp.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("stored-data-health-outcome", "data"),
    Input("stored-data-health-outcome", "data"),
)
def fetch_health_outcome_data_once(health_data):
    if health_data is None:
        uhc_index = db.get_universal_health_coverage_index()

        return {
            "uhc_index": uhc_index.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("stored-data-health-private", "data"),
    Input("stored-data-health-private", "data"),
)
def fetch_health_private_data_once(health_data):
    if health_data is None:
        priv_exp = db.get_health_private_expenditure()
        return {
            "health_private_expenditure": priv_exp.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("stored-data-health-sub-func", "data"),
    Input("stored-data-health-sub-func", "data"),
)
def fetch_health_sub_func_data_once(health_data):
    if health_data is None:
        exp_by_sub_func = db.get_expenditure_by_country_sub_func_year()
        return {
            "expenditure_by_country_sub_func_year": exp_by_sub_func.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("health-content", "children"),
    Input("health-tabs", "active_tab"),
)
def render_health_content(tab):
    if tab == "health-tab-time":
        return html.Div(
            [
                dbc.Row(
                    dbc.Col(
                        html.H3(
                            children="Who Pays for Healthcare?",
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="health-public-private-narrative",
                                children="loading...",
                            ),
                            html.P(
                                id="health-narrative",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="health-public-private",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                        dbc.Col(
                            dcc.Graph(
                                id="health-total",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                    ]
                ),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.H3(
                                children="Public Spending & Health Outcome",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="health-outcome",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 7, "offset": 0},
                        ),
                        dbc.Col(
                            [
                                html.P(
                                    id="health-outcome-measure",
                                    children="",
                                ),
                                html.P(
                                    id="health-outcome-narrative",
                                    children="loading...",
                                ),
                            ],
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 5, "offset": 0},
                        ),
                    ]
                ),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.H3(
                                children="Operational vs. Capital Spending",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(dcc.Store(id="page-selector", data="Health"), width=0),
                        dbc.Row(
                            [
                                dbc.Col(id="econ-breakdown-func-narrative-health", width=6),
                                dbc.Col(dcc.Graph(id="econ-breakdown-func-health"), width=6),
                            ]
                        ),
                    ]
                ),
            ]
        )
    elif tab == "health-tab-space":
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(width=1),
                        html.Div(
                            id="year_slider_health_container",
                            children=[
                                dcc.Slider(
                                    id="year-slider-health",
                                    min=0,
                                    max=0,
                                    value=None,
                                    step=None,
                                    included=False,
                                ),
                            ],
                        ),
                    ]
                ),
                dbc.Row(style={"height": "20px"}),
                dbc.Row(
                    dbc.Col(
                        html.H3(
                            children="Centrally vs. Geographically Allocated Health Spending",
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="health-sub-func-narrative",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(id="health-central-vs-regional"), width=5),
                        dbc.Col(dcc.Graph(id="health-sub-func"), width=7),
                    ]
                ),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.H3(
                            id="health-subnational-title",
                            children="Public Spending vs. Health Outcomes across Regions",
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                children="Disparities in public health spending across regions can impact Universal Health Coverage (UHC) by creating gaps in service access and financial protection. Since primary healthcare is central to UHC, regions with lower per capita health spending may struggle to provide essential services, leading to weaker coverage in maternal health, infectious disease control, and chronic disease management. Analyzing subnational disparities in geographically allocated health spending helps assess whether resources align with UHC goals and identify regions at risk of inadequate healthcare access.",
                            ),
                            html.P(
                                id="health-subnational-motivation",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.Div(
                            [
                                dbc.RadioItems(
                                    id="health-expenditure-type",
                                    options=[
                                        {
                                            "label": "Per capita health expenditure",
                                            "value": "per_capita_expenditure",
                                        },
                                        {
                                            "label": "Total health expenditure",
                                            "value": "expenditure",
                                        },
                                    ],
                                    value="per_capita_expenditure",
                                    inline=True,
                                    style={"padding": "10px"},
                                    labelStyle={
                                        "margin-right": "20px",
                                    },
                                ),
                                disclaimer_tooltip("health-expenditure-warning", MAP_DISCLAIMER),
                            ],
                            className="disclaimer-div",
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "space-between",
                                "width": "100%",
                            },
                        ),
                    ),
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="health-expenditure-map",
                                config={"displayModeBar": False},
                            ),
                            xs=12,
                            sm=12,
                            md=6,
                            lg=6,
                        ),
                        dbc.Col(
                            dcc.Graph(
                                id="health-outcome-map",
                                config={"displayModeBar": False},
                            ),
                            xs=12,
                            sm=12,
                            md=6,
                            lg=6,
                        ),
                    ]
                ),
                dbc.Row(style={"height": "20px"}),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="health-subnational-narrative",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="health-subnational",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 12, "offset": 0},
                        )
                    ]
                ),
            ],
        )


def total_health_figure(df):
    fig = go.Figure()

    if df is None:
        return fig
    fig.add_trace(
        go.Scatter(
            name="Inflation Adjusted",
            x=df.year,
            y=df.real_expenditure,
            mode="lines+markers",
            marker_color="darkblue",
        ),
    )
    fig.add_trace(
        go.Bar(
            name="Central",
            x=df.year,
            y=df.central_expenditure,
            marker_color="rgb(17, 141, 255)",
        ),
    )
    fig.add_trace(
        go.Bar(
            name="Regional",
            x=df.year,
            y=df.decentralized_expenditure,
            marker_color="rgb(160, 209, 255)",
        ),
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        barmode="stack",
        hovermode="x",
        title="How has govt spending on health changed over time?",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=-0,
                y=-0.2,
                text="Source: BOOST: World Bank",
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )

    return fig


def health_narrative(data, country):
    spending = pd.DataFrame(data["health_public_expenditure"])
    spending = filter_country_sort_year(spending, country)
    spending.dropna(subset=["real_expenditure", "central_expenditure"], inplace=True)

    start_year = spending.year.min()
    end_year = spending.year.max()
    start_value = spending[spending.year == start_year].real_expenditure.values[0]
    end_value = spending[spending.year == end_year].real_expenditure.values[0]
    spending_growth_rate = (end_value - start_value) / start_value
    trend = "increased" if end_value > start_value else "decreased"
    text = f"Between {start_year} and {end_year} after adjusting for inflation, total public spending on health in {country} has {trend} from ${millify(start_value)} to ${millify(end_value)}, reflecting a growth rate of {spending_growth_rate:.0%}. "

    spending["real_central_expenditure"] = (
        spending.real_expenditure / spending.expenditure * spending.central_expenditure
    )
    start_value_central = spending[
        spending.year == start_year
    ].real_central_expenditure.values[0]
    end_value_central = spending[
        spending.year == end_year
    ].real_central_expenditure.values[0]

    spending_growth_rate_central = (
        end_value_central - start_value_central
    ) / start_value_central

    text += f"In this time period, the central government's inflation-adjusted spending has {get_percentage_change_text(spending_growth_rate_central)} "

    if not np.isnan(
        spending[spending.year == start_year].decentralized_expenditure.values[0]
    ):
        spending["real_decentralized_expenditure"] = (
            spending.real_expenditure
            / spending.expenditure
            * spending.decentralized_expenditure
        )
        start_value_decentralized = spending[
            spending.year == start_year
        ].real_decentralized_expenditure.values[0]
        end_value_decentralized = spending[
            spending.year == end_year
        ].real_decentralized_expenditure.values[0]

        spending_growth_rate_decentralized = (
            end_value_decentralized - start_value_decentralized
        ) / start_value_decentralized
        spending_change_regional = f"while the subnational government's inflation-adjusted spending has {get_percentage_change_text(spending_growth_rate_decentralized)}. "
    else:
        spending_change_regional = (
            ". The subnational government's data is not available for this period. "
        )

    text += spending_change_regional

    decentralization = spending[
        spending.year == end_year
    ].expenditure_decentralization.values[0]
    if pd.isna(decentralization) or decentralization == 0:
        spending_decentralization = "The extent of health spending decentralization is unknown due to a lack of subnational public expenditure data."
    else:
        spending_decentralization = f"By {end_year}, {decentralization:.1%} of health spending has been decentralized."
    text += spending_decentralization

    return text


@callback(
    Output("health-total", "figure"),
    Output("health-narrative", "children"),
    Input("stored-data-health-total", "data"),
    Input("country-select", "value"),
)
def render_overview_total_figure(data, country):
    if data is None:
        return None

    all_countries = pd.DataFrame(data["health_public_expenditure"])
    df = filter_country_sort_year(all_countries, country)

    if df.empty:
        return (
            empty_plot("No data available for this period"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    fig = total_health_figure(df)
    return fig, health_narrative(data, country)


def public_private_narrative(df, country):
    latest_year = df.year.max()
    earliest_year = df.year.min()
    text = ""
    try:
        latest_gov_share = df[df.year == latest_year].public_percentage.values[0]
        earliest_gov_share = df[df.year == earliest_year].public_percentage.values[0]
        trend = "increased" if latest_gov_share > earliest_gov_share else "decreased"
        household_ratio = (
            df[df.year == latest_year].real_expenditure_private.values[0]
            / df.real_expenditure_public.values[0]
        )
        if earliest_year != latest_year:
            text += f"In {country}, the government's share of spending on health {trend} from {earliest_gov_share:.0%} to {latest_gov_share:.0%} between {earliest_year} and {latest_year}. "

        text += f"For every unit of spending on health by the government, households spent {household_ratio:.1f} units in {latest_year}. "

    except IndexError:
        return generate_error_prompt("DATA_UNAVAILABLE")
    except:
        return generate_error_prompt("GENERIC_ERROR")
    return text


@callback(
    Output("health-public-private", "figure"),
    Output("health-public-private-narrative", "children"),
    Input("stored-data-health-private", "data"),
    Input("stored-data-health-total", "data"),
    Input("country-select", "value"),
)
def render_public_private_figure(private_data, public_data, country):
    if not private_data or not public_data:
        return

    fig_title = "What % was spent by the govt vs household?"

    private = pd.DataFrame(private_data["health_private_expenditure"])
    private = filter_country_sort_year(private, country)

    public_data = pd.DataFrame(public_data["health_public_expenditure"])
    public = filter_country_sort_year(public_data, country)

    merged = pd.merge(
        private,
        public,
        on=["year", "country_name"],
        how="inner",
        suffixes=["_private", "_public"],
    )
    merged = merged.dropna(
        subset=["real_expenditure_public", "real_expenditure_private"]
    )

    if merged.empty:
        if public.empty:
            prompt = generate_error_prompt(
                "DATA_UNAVAILABLE_DATASET_NAME", dataset_name="health public spending"
            )
        elif private.empty:
            prompt = generate_error_prompt(
                "DATA_UNAVAILABLE_DATASET_NAME", dataset_name="health private spending"
            )
        else:
            prompt = "Available public and private spending data on health do not have an overlapping time period."
        return (empty_plot(prompt, fig_title=fig_title), prompt)

    merged["private_percentage"] = merged["real_expenditure_private"] / (
        merged["real_expenditure_private"] + merged["real_expenditure_public"]
    )
    merged["public_percentage"] = 1 - merged["private_percentage"]

    merged["real_expenditure_private_formatted"] = merged[
        "real_expenditure_private"
    ].apply(millify)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Private Expenditure",
            y=merged["year"].astype(str),
            x=merged.private_percentage,
            orientation="h",
            customdata=merged.real_expenditure_private_formatted,
            hovertemplate="%{customdata}",
            marker=dict(
                color="rgb(255, 191, 0)",
            ),
            text=merged.private_percentage,
            texttemplate="%{text:.0%}",
            textposition="auto",
        )
    )

    merged["real_expenditure_public_formatted"] = merged[
        "real_expenditure_public"
    ].apply(millify)
    fig.add_trace(
        go.Bar(
            name="Public Expenditure",
            y=merged["year"].astype(str),
            x=merged.public_percentage,
            orientation="h",
            customdata=merged.real_expenditure_public_formatted,
            hovertemplate="$%{customdata}",
            marker=dict(
                color="darkblue",
            ),
            text=merged.public_percentage,
            texttemplate="%{text:.0%}",
            textposition="auto",
        )
    )
    fig.update_layout(
        barmode="stack",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1),
        title=fig_title,
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=-0,
                y=-0.2,
                text="Source: Household exp: WHO, Public exp from BOOST: World Bank",
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )

    narrative = public_private_narrative(merged, country)
    return fig, narrative


def outcome_measure():
    return f"We use inflation-adjusted per capita public spending as a measure for public financial resource allocation per person on health and universal health coverage index as an indicator for health outcome."


def outcome_narrative(outcome_df, expenditure_df, country):
    try:
        start_year = expenditure_df.year.min()
        end_year = expenditure_df.year.max()

        merged = pd.merge(outcome_df, expenditure_df, on=["year"], how="inner")
        x_col = {
            "display": "universal health coverage index",
            "col_name": "universal_health_coverage_index",
        }
        y_col = {
            "display": "per capita public spending",
            "col_name": "per_capita_real_expenditure",
        }
        PCC = get_correlation_text(merged, x_col, y_col)

        text = f"From {start_year} to {end_year}, {PCC}"
    except:
        traceback.print_exc()
        return generate_error_prompt("GENERIC_ERROR")
    return text


@callback(
    Output("health-outcome", "figure"),
    Output("health-outcome-measure", "children"),
    Output("health-outcome-narrative", "children"),
    Input("stored-data-health-outcome", "data"),
    Input("stored-data-health-total", "data"),
    Input("country-select", "value"),
)
def render_health_outcome(outcome_data, total_data, country):
    if not total_data or not outcome_data:
        return

    uhc = pd.DataFrame(outcome_data["uhc_index"])
    uhc = filter_country_sort_year(uhc, country)

    pub_exp = pd.DataFrame(total_data["health_public_expenditure"])
    pub_exp = filter_country_sort_year(pub_exp, country)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            name="Universal health coverage index",
            x=uhc.year,
            y=uhc.universal_health_coverage_index,
            mode="lines+markers",
            line=dict(color="deeppink", shape="spline", dash="dot"),
            connectgaps=True,
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            name="Inflation adjusted per capita public spending",
            x=pub_exp.year,
            y=pub_exp.per_capita_real_expenditure,
            mode="lines",
            marker_color="darkblue",
            opacity=0.6,
        ),
        secondary_y=False,
    )

    fig.update_layout(
        plot_bgcolor="white",
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.95,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
        ),
        title=dict(
            text="How has health outcome changed?",
            y=0.95,
            x=0.5,
            xanchor="center",
            yanchor="top",
        ),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=-0,
                y=-0.2,
                text="Source: UHC: WHO; BOOST: World Bank; Population: UN, Eurostat",
                showarrow=False,
                font=dict(size=12),
            )
        ],
        hoverlabel_namelength=-1,
    )

    fig.update_yaxes(
        range=[0, max(pub_exp.per_capita_real_expenditure) * 1.2], secondary_y=False
    )
    fig.update_yaxes(range=[0, 120], secondary_y=True)

    narrative = outcome_narrative(uhc, pub_exp, country)
    return fig, outcome_measure(), narrative


@callback(
    [
        Output("econ-breakdown-func-health", "figure"),
        Output("econ-breakdown-func-narrative-health", "children"),
        Input("stored-data-func-econ", "data"),
        Input("country-select", "value"),
        Input("page-selector", "data"),
    ],
)
def render_operational_vs_capital_breakdown(data, country_name, page_func):
    return render_econ_breakdown(data, country_name, page_func)


@callback(
    Output("year_slider_health_container", "style"),
    Output("year-slider-health", "marks"),
    Output("year-slider-health", "value"),
    Output("year-slider-health", "min"),
    Output("year-slider-health", "max"),
    Output("year-slider-health", "tooltip"),
    Input("stored-data-subnational", "data"),
    Input("country-select", "value"),
)
def update_health_year_range(data, country):
    return update_year_slider(data, country, 'Health')


@callback(
    Output("health-central-vs-regional", "figure"),
    Output("health-sub-func", "figure"),
    Output("health-sub-func-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("stored-data-subnational", "data"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
)
def render_health_subnat_overview(func_data, sub_func_data, country, selected_year):
    return render_func_subnat_overview(
        func_data, sub_func_data, country, selected_year, 'Health'
    )

@callback(
    Output("health-subnational-motivation", "children"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
)
def update_health_subnational_motivation_narrative(country_name, year):
    narrative = f'To examine this for {country_name}, we analyze per capita public health spending in {year} as a measure of financial resource allocation at the subnational level and use the UHC index as an indicator of Universal Health Coverage.'
    return narrative


@callback(
    Output("health-expenditure-map", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
    Input("health-expenditure-type", "value"),
    Input("stored-data-subnat-boundaries", "data"),
)
def update_health_expenditure_map(
    subnational_data, country_data, country, year, expenditure_type, subnat_boundaries,
):
    return update_func_expenditure_map(
        subnational_data, country_data, country, year,
        expenditure_type, subnat_boundaries, 'Health'
    )


@callback(
    Output("health-outcome-map", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
    Input("stored-data-subnat-boundaries", "data"),
)
def update_health_index_map(
    subnational_data, country_data, country, year, subnat_boundaries,
):
    return update_hd_index_map(
        subnational_data, country_data, country, year, subnat_boundaries, 'Health'
    )


@callback(
    Output("health-subnational", "figure"),
    Output("health-subnational-narrative", "children"),
    Input("stored-data-subnational", "data"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
)
def render_health_subnat_rank(subnational_data, country, base_year):
    return render_func_subnat_rank(subnational_data, country, base_year, 'Health')
