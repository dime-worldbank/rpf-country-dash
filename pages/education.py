import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from constants import MAP_DISCLAIMER
from queries import QueryService
from utils import (
    add_currency_column,
    empty_plot,
    filter_country_sort_year,
    format_currency,
    generate_error_prompt,
    get_percentage_change_text,
    millify,
    require_login,
)
import numpy as np
from components.year_slider import slider, get_slider_config
from components.func_operational_vs_capital_spending import render_econ_breakdown
from components.edu_health_across_space import (
    update_year_slider,
    render_func_subnat_overview,
    update_func_expenditure_map,
    update_hd_index_map,
    render_func_subnat_rank,
)
from components.disclaimer_div import disclaimer_tooltip
from components.source_metadata_popover import source_info_button, empty_modal
from trend_narrative import get_relationship_narrative, get_segment_narrative, InsightExtractor

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
                            id="education-tabs",
                            active_tab="edu-tab-time",
                            children=[
                                dbc.Tab(label="Over Time", tab_id="edu-tab-time"),
                                dbc.Tab(label="Across Space", tab_id="edu-tab-space"),
                            ],
                            style={"marginBottom": "2rem"},
                        ),
                        html.Div(id="education-content"),
                    ]
                ),
            ),
            dcc.Store(id="stored-data-education-total"),
            dcc.Store(id="stored-data-education-outcome"),
            dcc.Store(id="stored-data-education-private"),
        ]
    )


@callback(
    Output("stored-data-education-total", "data"),
    Input("stored-data-education-total", "data"),
    Input("stored-data-func-econ", "data"),
)
def fetch_edu_total_data_once(edu_data, shared_data):
    if edu_data is None:
        # filter shared data down to education specific
        exp_by_func = pd.DataFrame(shared_data["expenditure_by_country_func_year"])
        pub_exp = exp_by_func[exp_by_func.func == "Education"]

        return {
            "edu_public_expenditure": pub_exp.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("stored-data-education-outcome", "data"),
    Input("stored-data-education-outcome", "data"),
    Input("stored-data", "data"),
)
def fetch_edu_outcome_data_once(edu_data, shared_data):
    if edu_data is None:
        learning_poverty = db.get_learning_poverty_rate()

        hd_index = db.get_hd_index(shared_data["countries"])

        return {
            "learning_poverty": learning_poverty.to_dict("records"),
            "hd_index": hd_index.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("stored-data-education-private", "data"),
    Input("stored-data-education-private", "data"),
)
def fetch_edu_private_data_once(edu_data):
    if edu_data is None:
        priv_exp = db.get_edu_private_expenditure()
        return {
            "edu_private_expenditure": priv_exp.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("education-content", "children"),
    Input("education-tabs", "active_tab"),
)
def render_education_content(tab):
    if tab == "edu-tab-time":
        return html.Div(
            [
                dbc.Row(
                    dbc.Col(
                        html.H3(children="Who Pays for Education?")
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="education-public-private-narrative",
                                children="loading...",
                            ),
                            html.P(
                                id="education-narrative",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div([
                                html.Div(source_info_button("edu-public-private"), style={"textAlign": "right"}),
                                dcc.Graph(
                                    id="education-public-private",
                                    config={"displayModeBar": False},
                                ),
                                empty_modal("edu-public-private"),
                            ]),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                        dbc.Col(
                            html.Div([
                                html.Div(source_info_button("edu-total"), style={"textAlign": "right"}),
                                dcc.Graph(
                                    id="education-total",
                                    config={"displayModeBar": False},
                                ),
                                empty_modal("edu-total"),
                            ]),
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
                        html.H3(children="Public Spending & Education Outcome")
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div([
                                html.Div(source_info_button("edu-outcome"), style={"textAlign": "right"}),
                                dcc.Graph(
                                    id="education-outcome",
                                    config={"displayModeBar": False},
                                ),
                                empty_modal("edu-outcome"),
                            ]),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 7, "offset": 0},
                        ),
                        dbc.Col(
                            [
                                html.P(
                                    children="Generally, while education outcomes related to access can be conceptually linked to the availability of public finance, results related to quality have a more complex chain of causality.",
                                ),
                                html.P(
                                    id="education-outcome-measure",
                                    children="",
                                ),
                                html.P(
                                    id="education-outcome-narrative",
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
                        html.H3(children="Operational vs. Capital Spending")
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Store(id="page-selector", data="Education"), width=0
                        ),
                        dbc.Row(
                            [
                                dbc.Col(id="econ-breakdown-func-narrative-edu", width=6),
                                dbc.Col(
                                    html.Div([
                                        html.Div(source_info_button("edu-opvcap"), style={"textAlign": "right"}),
                                        dcc.Graph(id="econ-breakdown-func-edu"),
                                        empty_modal("edu-opvcap"),
                                    ]),
                                    width=6
                                ),
                            ]
                        ),
                    ]
                ),
            ]
        )
    elif tab == "edu-tab-space":
        return html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(width=1),
                        html.Div(
                            id="year_slider_edu_container",
                            children=[
                                dcc.Slider(
                                    id="year-slider-edu",
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
                        html.H3(children="Centrally vs. Geographically Allocated Education Spending")
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="education-sub-func-narrative",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div([
                                html.Div(source_info_button("edu-central-regional"), style={"textAlign": "right"}),
                                dcc.Graph(id="education-central-vs-regional"),
                                empty_modal("edu-central-regional"),
                            ]),
                            width=5
                        ),
                        dbc.Col(
                            html.Div([
                                html.Div(source_info_button("edu-sub-func"), style={"textAlign": "right"}),
                                dcc.Graph(id="education-sub-func"),
                                empty_modal("edu-sub-func"),
                            ]),
                            width=7
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
                        html.H3(
                            id="education-subnational-title",
                            children="Public Spending vs. Education Outcomes across Regions",
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                children="Since primary and secondary education are more directly linked to school attendance among children aged 6-17, disparities in their funding at the regional level may have a stronger impact on access to education. Understanding how these resources translate into education access is critical for assessing whether public spending effectively supports equitable opportunities for children. If funding is unevenly distributed, it may contribute to disparities in school attendance across regions.",
                            ),
                            html.P(
                                id="education-subnational-motivation",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    html.Div(
                        [
                            dbc.RadioItems(
                                id="education-expenditure-type",
                                options=[
                                    {
                                        "label": "Per capita education expenditure",
                                        "value": "per_capita_expenditure",
                                    },
                                    {
                                        "label": "Total education expenditure",
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
                            disclaimer_tooltip("education-expenditure-warning", MAP_DISCLAIMER),
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
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div([
                                html.Div(source_info_button("edu-expenditure-map"), style={"textAlign": "right"}),
                                dcc.Graph(
                                    id="education-expenditure-map",
                                    config={"displayModeBar": False},
                                ),
                                empty_modal("edu-expenditure-map"),
                            ]),
                            xs=12,
                            sm=12,
                            md=6,
                            lg=6,
                        ),
                        dbc.Col(
                            html.Div([
                                html.Div(source_info_button("edu-outcome-map"), style={"textAlign": "right"}),
                                dcc.Graph(
                                    id="education-outcome-map",
                                    config={"displayModeBar": False},
                                ),
                                empty_modal("edu-outcome-map"),
                            ]),
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
                                id="education-subnational-narrative",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div([
                                html.Div(source_info_button("edu-subnational"), style={"textAlign": "right"}),
                                dcc.Graph(
                                    id="education-subnational",
                                    config={"displayModeBar": False},
                                ),
                                empty_modal("edu-subnational"),
                            ]),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 12, "offset": 0},
                        )
                    ]
                ),
            ],
        )


def total_edu_figure(df, currency_code):
    add_currency_column(df, 'central_expenditure', currency_code)
    add_currency_column(df, 'decentralized_expenditure', currency_code)
    add_currency_column(df, 'real_expenditure', currency_code)
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
            customdata=np.column_stack([df.real_expenditure_formatted]),
            hovertemplate="<b>Real Expenditure</b>: %{customdata[0]}<extra></extra>",
        ),
    )
    fig.add_trace(
        go.Bar(
            name="Central",
            x=df.year,
            y=df.central_expenditure,
            marker_color="rgb(17, 141, 255)",
            customdata=np.column_stack([df.central_expenditure_formatted]),
            hovertemplate="<b>Central</b>: %{customdata[0]}<extra></extra>",
        ),
    )
    fig.add_trace(
        go.Bar(
            name="Regional",
            x=df.year,
            y=df.decentralized_expenditure,
            marker_color="rgb(160, 209, 255)",
            customdata=np.column_stack([df.decentralized_expenditure_formatted]),
            hovertemplate="<b>Regional</b>: %{customdata[0]}<extra></extra>",
        ),
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        barmode="stack",
        hovermode="x unified",
        title="How has govt spending on education changed over time?",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1),
    )

    return fig


def education_narrative(data, country):
    spending = pd.DataFrame(data["edu_public_expenditure"])
    spending = filter_country_sort_year(spending, country)

    plot_df = (
        spending.dropna(subset=["real_expenditure"])
        .groupby("year")["real_expenditure"].sum()
        .reset_index()
        .sort_values("year")
    )
    extractor = InsightExtractor(plot_df["year"].values, plot_df["real_expenditure"].values)
    trend_narrative = get_segment_narrative(extractor=extractor, metric="real expenditure")

    if trend_narrative:
        trend_narrative = trend_narrative[0].lower() + trend_narrative[1:]
        text = f"After accounting for inflation, {trend_narrative} "
    else:
        text = ""

    spending = spending.dropna(subset=["real_expenditure", "central_expenditure"])
    start_year = spending.year.min()
    end_year = spending.year.max()

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
        spending_decentralization = "The extent of education spending decentralization is unknown due to a lack of subnational public expenditure data."
    else:
        spending_decentralization = f"By {end_year}, {decentralization:.1%} of education spending has been decentralized."
    text += spending_decentralization

    return text


@callback(
    Output("education-total", "figure"),
    Output("education-narrative", "children"),
    Input("stored-data-education-total", "data"),
    Input('stored-basic-country-data', 'data'),
    Input("country-select", "value"),
)
def render_overview_total_figure(data, basic_country_data, country):
    if data is None:
        return None

    all_countries = pd.DataFrame(data["edu_public_expenditure"])
    df = filter_country_sort_year(all_countries, country)
    basic_info = pd.DataFrame(basic_country_data['basic_country_info']).T.loc[country]
    currency_code = basic_info['currency_code']

    if df.empty:
        return (
            empty_plot("No data available for this period"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    fig = total_edu_figure(df, currency_code)
    return fig, education_narrative(data, country)


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
            text += f"In {country}, the government's share of spending on education {trend} from {earliest_gov_share:.0%} to {latest_gov_share:.0%} between {earliest_year} and {latest_year}. "

        text += f"For every unit of spending on education by the government, households spent {household_ratio:.1f} units in {latest_year}. "

    except IndexError:
        return generate_error_prompt("DATA_UNAVAILABLE")
    except:
        return generate_error_prompt("GENERIC_ERROR")
    return text


@callback(
    Output("education-public-private", "figure"),
    Output("education-public-private-narrative", "children"),
    Input("stored-data-education-private", "data"),
    Input("stored-data-education-total", "data"),
    Input("country-select", "value"),
    Input('stored-basic-country-data', 'data')
)
def render_public_private_figure(private_data, public_data, country,basic_country_data):
    if not private_data or not public_data:
        return
    
    currency_code = pd.DataFrame(basic_country_data['basic_country_info']).T.loc[country]['currency_code']
    fig_title = "What % was spent by the govt vs household?"

    private = pd.DataFrame(private_data["edu_private_expenditure"])
    private = filter_country_sort_year(private, country)

    public_data = pd.DataFrame(public_data["edu_public_expenditure"])
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
                "DATA_UNAVAILABLE_DATASET_NAME",
                dataset_name="Education public spending",
            )
        elif private.empty:
            prompt = generate_error_prompt(
                "DATA_UNAVAILABLE_DATASET_NAME",
                dataset_name="Education private spending",
            )
        else:
            prompt = "Available public and private spending data on education do not have an overlapping time period."
        return (empty_plot(prompt, fig_title=fig_title), prompt)

    merged["private_percentage"] = merged["real_expenditure_private"] / (
        merged["real_expenditure_private"] + merged["real_expenditure_public"]
    )
    merged["public_percentage"] = 1 - merged["private_percentage"]

    add_currency_column(merged, 'real_expenditure_private', currency_code)
    add_currency_column(merged, 'real_expenditure_public', currency_code)
    fig = go.Figure()



    fig.add_trace(
        go.Bar(
            name="Public Expenditure",
            y=merged["year"].astype(str),
            x=merged.public_percentage,
            orientation="h",
            customdata=merged.real_expenditure_public_formatted,
            hovertemplate="%{customdata}",
            marker=dict(
                color="darkblue",
            ),
            text=merged.public_percentage,
            texttemplate="%{text:.0%}",
            textposition="auto",
        )
    )

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
    fig.update_layout(
        barmode="stack",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1, traceorder="normal"),
        title=fig_title,
    )

    narrative = public_private_narrative(merged, country)
    return fig, narrative


def outcome_measure(country):
    return f"To check if this is the case for {country}, we can use inflation-adjusted per capita public spending as a measure for public financial resource allocation per person on education, use school attendance rate of 6-17 year-old children to proximate access to education, and use learning poverty rate as an indicator for education quality."


def outcome_narrative(outcome_df, pov_df, expenditure_df, country, currency_code):
    exp_df = expenditure_df.dropna(subset=["per_capita_real_expenditure"])
    att_df = outcome_df.dropna(subset=["attendance_6to17yo"])
    pov_df_clean = pov_df.dropna(subset=["learning_poverty_rate"])

    spending_fmt = lambda x: format_currency(x, currency_code)

    attendance_result = get_relationship_narrative(
        reference_years=exp_df["year"].values,
        reference_values=exp_df["per_capita_real_expenditure"].values,
        comparison_years=att_df["year"].values,
        comparison_values=att_df["attendance_6to17yo"].values,
        reference_name="per capita education spending",
        comparison_name="school attendance (6-17 year-olds)",
        reference_format=spending_fmt,
        comparison_format=".1f",
    )

    poverty_result = get_relationship_narrative(
        reference_years=exp_df["year"].values,
        reference_values=exp_df["per_capita_real_expenditure"].values,
        comparison_years=pov_df_clean["year"].values,
        comparison_values=pov_df_clean["learning_poverty_rate"].values,
        reference_name="per capita education spending",
        comparison_name="learning poverty rate",
        reference_format=spending_fmt,
        comparison_format=".1f",
    )

    both_insufficient = (
        attendance_result["method"] == "insufficient_data" and
        poverty_result["method"] == "insufficient_data"
    )
    if both_insufficient:
        return "The relationship between education spending and outcomes cannot be determined due to limited data availability."

    poverty_narrative = poverty_result["narrative"]
    poverty_narrative = poverty_narrative[0].lower() + poverty_narrative[1:]
    return f"{attendance_result['narrative']} Meanwhile, {poverty_narrative}"


@callback(
    Output("education-outcome", "figure"),
    Output("education-outcome-measure", "children"),
    Output("education-outcome-narrative", "children"),
    Input("stored-data-education-outcome", "data"),
    Input("stored-data-education-total", "data"),
    Input("country-select", "value"),
    Input('stored-basic-country-data', 'data')
)
def render_education_outcome(outcome_data, total_data, country, basic_country_data):
    if not total_data or not outcome_data:
        return

    indicator = pd.DataFrame(outcome_data["hd_index"])
    indicator = filter_country_sort_year(indicator, country)
    indicator = indicator[indicator.adm1_name == "Total"]

    learning_poverty = pd.DataFrame(outcome_data["learning_poverty"])
    learning_poverty = filter_country_sort_year(learning_poverty, country)

    pub_exp = pd.DataFrame(total_data["edu_public_expenditure"])
    pub_exp = filter_country_sort_year(pub_exp, country)

    currency_code = pd.DataFrame(basic_country_data['basic_country_info']).T.loc[country]['currency_code']

    add_currency_column(pub_exp, 'per_capita_real_expenditure', currency_code)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            name="6-17yo attendance rate",
            x=indicator.year,
            y=indicator.attendance_6to17yo,
            mode="lines+markers",
            line=dict(color="MediumPurple", shape="spline", dash="dot"),
            connectgaps=True,
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            name="learning poverty rate",
            x=learning_poverty.year,
            y=learning_poverty.learning_poverty_rate,
            mode="lines+markers",
            line=dict(color="deeppink", shape="spline", dash="dot"),
            connectgaps=True,
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            name="inflation adjusted per capita public spending",
            x=pub_exp.year,
            y=pub_exp.per_capita_real_expenditure,
            mode="lines",
            marker_color="darkblue",
            opacity=0.6,
            customdata=np.column_stack([pub_exp.per_capita_real_expenditure_formatted]),
            hovertemplate="Inflation Adjusted Per Capita Public Spending: %{customdata[0]}<extra></extra>",
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
        hovermode="x unified",
        title=dict(
            text="How has education outcome changed?",
            y=0.95,
            x=0.5,
            xanchor="center",
            yanchor="top",
        ),
        hoverlabel_namelength=-1,
    )

    fig.update_yaxes(
        range=[0, max(pub_exp.per_capita_real_expenditure) * 1.2], secondary_y=False
    )
    fig.update_yaxes(range=[0, 1.2], tickformat=".0%", secondary_y=True)

    measure = outcome_measure(country)
    narrative = outcome_narrative(indicator, learning_poverty, pub_exp, country, currency_code)
    return fig, measure, narrative


@callback(
    [
        Output("econ-breakdown-func-edu", "figure"),
        Output("econ-breakdown-func-narrative-edu", "children"),
        Input("stored-data-func-econ", "data"),
        Input("country-select", "value"),
        Input("page-selector", "data"),
    ],
)
def render_operational_vs_capital_breakdown(data, country_name, page_func):
    return render_econ_breakdown(data, country_name, page_func)


@callback(
    Output("year_slider_edu_container", "style"),
    Output("year-slider-edu", "marks"),
    Output("year-slider-edu", "value"),
    Output("year-slider-edu", "min"),
    Output("year-slider-edu", "max"),
    Output("year-slider-edu", "tooltip"),
    Input("stored-data-subnational", "data"),
    Input("country-select", "value"),
)
def update_education_year_range(data, country):
    return update_year_slider(data, country, 'Education')


@callback(
    Output("education-central-vs-regional", "figure"),
    Output("education-sub-func", "figure"),
    Output("education-sub-func-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("stored-data-subnational", "data"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
    Input('stored-basic-country-data', 'data')
)
def render_education_subnat_overview(func_econ_data, sub_func_data, country, selected_year, country_data):
    currency_code = country_data['basic_country_info'][country]['currency_code']
    return render_func_subnat_overview(
        func_econ_data, sub_func_data, country, selected_year, 'Education', currency_code
    )


@callback(
    Output("education-subnational-motivation", "children"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
)
def update_education_subnational_motivation_narrative(country_name, year):
    narrative = f'To examine this for {country_name}, we analyze per capita public spending on education in {year} as a measure of financial resource allocation at the subnational level and use the school attendance rate of 6-17-year-old children to approximate access to education.'
    return narrative


@callback(
    Output("education-expenditure-map", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
    Input("education-expenditure-type", "value"),
    Input("stored-data-subnat-boundaries", "data"),
)
def update_education_expenditure_map(
    subnational_data, country_data, country, year, expenditure_type, subnat_boundaries
):
    return update_func_expenditure_map(
        subnational_data, country_data, country, year,
        expenditure_type, subnat_boundaries, 'Education'
    )


@callback(
    Output("education-outcome-map", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
    Input("stored-data-subnat-boundaries", "data"),
)
def update_education_index_map(
    subnational_data, country_data, country, year, subnat_boundaries
):
    return update_hd_index_map(
        subnational_data, country_data, country, year, subnat_boundaries, 'Education'
    )


@callback(
    Output("education-subnational", "figure"),
    Output("education-subnational-narrative", "children"),
    Input("stored-data-subnational", "data"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
    Input('stored-basic-country-data', 'data'),
)
def render_education_subnat_rank(subnational_data, country, base_year, country_data):
    currency_code = country_data['basic_country_info'][country]['currency_code']
    return render_func_subnat_rank(subnational_data, country, base_year, 'Education', currency_code)
