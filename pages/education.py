import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from constants import get_map_disclaimer
from translations import t
from viz_theme import CENTRAL_COLOR, REGIONAL_COLOR
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
from components.source_metadata_popover import chart_container, empty_modal
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
    Output("education-tabs", "children"),
    Input("stored-language", "data"),
)
def update_edu_tab_labels(lang):
    return [
        dbc.Tab(label=t("tab.over_time", lang), tab_id="edu-tab-time"),
        dbc.Tab(label=t("tab.across_space", lang), tab_id="edu-tab-space"),
    ]


@callback(
    Output("stored-data-education-total", "data"),
    Input("stored-data-education-total", "data"),
    Input("stored-data-func-econ", "data"),
)
def fetch_edu_total_data_once(edu_data, shared_data):
    if edu_data is None and shared_data:
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
    if edu_data is None and shared_data:
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
    Input("stored-language", "data"),
)
def render_education_content(tab, lang):
    lang = lang or "en"
    if tab == "edu-tab-time":
        return html.Div(
            [
                dbc.Row(
                    dbc.Col(
                        html.H3(children=t("heading.who_pays_education", lang))
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="education-public-private-narrative",
                                children=t("loading", lang),
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
                            chart_container("education-public-private"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                        dbc.Col(
                            chart_container("education-total"),
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
                        html.H3(children=t("heading.public_spending_education_outcome", lang))
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            chart_container("education-outcome"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 7, "offset": 0},
                        ),
                        dbc.Col(
                            [
                                html.P(
                                    children=t("narrative.education_outcome_general", lang),
                                ),
                                html.P(
                                    id="education-outcome-measure",
                                    children="",
                                ),
                                html.P(
                                    id="education-outcome-narrative",
                                    children=t("loading", lang),
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
                        html.H3(children=t("heading.operational_vs_capital", lang))
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
                                    chart_container("econ-breakdown-func-edu"),
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
                        html.H3(children=t("heading.central_vs_geo_education", lang))
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="education-sub-func-narrative",
                                children=t("loading", lang),
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            chart_container("education-central-vs-regional"),
                            width=5
                        ),
                        dbc.Col(
                            chart_container("education-sub-func"),
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
                            children=t("heading.public_spending_education_regions", lang),
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                children=t("narrative.edu_subnational_context", lang),
                            ),
                            html.P(
                                id="education-subnational-motivation",
                                children=t("loading", lang),
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
                                        "label": t("radio.per_capita_expenditure", lang, sector="education"),
                                        "value": "per_capita_expenditure",
                                    },
                                    {
                                        "label": t("radio.total_expenditure", lang, sector="education"),
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
                            disclaimer_tooltip("education-expenditure-warning", get_map_disclaimer(lang), lang=lang),
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
                            chart_container("education-expenditure-map"),
                            xs=12,
                            sm=12,
                            md=6,
                            lg=6,
                        ),
                        dbc.Col(
                            chart_container("education-outcome-map"),
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
                                children=t("loading", lang),
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            chart_container("education-subnational"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 12, "offset": 0},
                        )
                    ]
                ),
            ],
        )


def total_edu_figure(df, currency_code, lang="en"):
    add_currency_column(df, 'central_expenditure', currency_code)
    add_currency_column(df, 'decentralized_expenditure', currency_code)
    add_currency_column(df, 'real_expenditure', currency_code)
    fig = go.Figure()

    if df is None:
        return fig
    fig.add_trace(
        go.Scatter(
            name=t("trace.inflation_adjusted", lang),
            x=df.year,
            y=df.real_expenditure,
            mode="lines+markers",
            marker_color="darkblue",
            customdata=np.column_stack([df.real_expenditure_formatted]),
            hovertemplate="<b>" + t("hover.real_expenditure", lang) + "</b>: %{customdata[0]}<extra></extra>",
        ),
    )
    fig.add_trace(
        go.Bar(
            name=t("trace.central", lang),
            x=df.year,
            y=df.central_expenditure,
            marker_color=CENTRAL_COLOR,
            customdata=np.column_stack([df.central_expenditure_formatted]),
            hovertemplate="<b>" + t("hover.central", lang) + "</b>: %{customdata[0]}<extra></extra>",
        ),
    )
    fig.add_trace(
        go.Bar(
            name=t("trace.regional", lang),
            x=df.year,
            y=df.decentralized_expenditure,
            marker_color=REGIONAL_COLOR,
            customdata=np.column_stack([df.decentralized_expenditure_formatted]),
            hovertemplate="<b>" + t("hover.regional", lang) + "</b>: %{customdata[0]}<extra></extra>",
        ),
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        barmode="stack",
        hovermode="x unified",
        title=t("chart.edu_spending_over_time", lang),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1),
    )

    return fig


def education_narrative(data, country, lang="en"):
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
        text = t("narrative.after_inflation", lang, trend_narrative=trend_narrative)
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

    text += t("narrative.central_spending_change", lang, change_text=get_percentage_change_text(spending_growth_rate_central, lang=lang))

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
        spending_change_regional = t("narrative.subnational_spending_change", lang, change_text=get_percentage_change_text(spending_growth_rate_decentralized, lang=lang))
    else:
        spending_change_regional = t("narrative.subnational_unavailable", lang)

    text += spending_change_regional

    decentralization = spending[
        spending.year == end_year
    ].expenditure_decentralization.values[0]
    if pd.isna(decentralization) or decentralization == 0:
        spending_decentralization = t("narrative.decentralization_unknown", lang, sector="education")
    else:
        spending_decentralization = t("narrative.decentralization_by_year", lang, year=end_year, pct=f"{decentralization:.1%}", sector="education")
    text += spending_decentralization

    return text


@callback(
    Output("education-total", "figure"),
    Output("education-narrative", "children"),
    Input("stored-data-education-total", "data"),
    Input('stored-basic-country-data', 'data'),
    Input("country-select", "value"),
    Input("stored-language", "data"),
)
def render_overview_total_figure(data, basic_country_data, country, lang):
    lang = lang or "en"
    if not data or not basic_country_data:
        return dash.no_update, dash.no_update

    all_countries = pd.DataFrame(data["edu_public_expenditure"])
    df = filter_country_sort_year(all_countries, country)
    basic_info = pd.DataFrame(basic_country_data['basic_country_info']).T.loc[country]
    currency_code = basic_info['currency_code']

    if df.empty:
        return (
            empty_plot(t("error.no_data_period", lang)),
            generate_error_prompt("DATA_UNAVAILABLE", lang=lang),
        )

    fig = total_edu_figure(df, currency_code, lang=lang)
    return fig, education_narrative(data, country, lang=lang)


def public_private_narrative(df, country, lang="en"):
    latest_year = df.year.max()
    earliest_year = df.year.min()
    text = ""
    try:
        latest_gov_share = df[df.year == latest_year].public_percentage.values[0]
        earliest_gov_share = df[df.year == earliest_year].public_percentage.values[0]
        trend = t("word.increased", lang) if latest_gov_share > earliest_gov_share else t("word.decreased", lang)
        household_ratio = (
            df[df.year == latest_year].real_expenditure_private.values[0]
            / df.real_expenditure_public.values[0]
        )
        if earliest_year != latest_year:
            text += t("narrative.govt_share_trend", lang,
                       country=country, sector="education", trend=trend,
                       earliest_pct=f"{earliest_gov_share:.0%}",
                       latest_pct=f"{latest_gov_share:.0%}",
                       earliest_year=earliest_year, latest_year=latest_year)

        text += t("narrative.household_ratio", lang, sector="education",
                   ratio=f"{household_ratio:.1f}", year=latest_year)

    except IndexError:
        return generate_error_prompt("DATA_UNAVAILABLE", lang=lang)
    except:
        return generate_error_prompt("GENERIC_ERROR", lang=lang)
    return text


@callback(
    Output("education-public-private", "figure"),
    Output("education-public-private-narrative", "children"),
    Input("stored-data-education-private", "data"),
    Input("stored-data-education-total", "data"),
    Input("country-select", "value"),
    Input('stored-basic-country-data', 'data'),
    Input("stored-language", "data"),
)
def render_public_private_figure(private_data, public_data, country, basic_country_data, lang):
    lang = lang or "en"
    if not private_data or not public_data:
        return dash.no_update, dash.no_update

    currency_code = pd.DataFrame(basic_country_data['basic_country_info']).T.loc[country]['currency_code']
    fig_title = t("chart.pct_govt_vs_household", lang)

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
                lang=lang,
                dataset_name="Education public spending",
            )
        elif private.empty:
            prompt = generate_error_prompt(
                "DATA_UNAVAILABLE_DATASET_NAME",
                lang=lang,
                dataset_name="Education private spending",
            )
        else:
            prompt = t("error.no_overlapping_data", lang, sector="education")
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
            name=t("trace.public_expenditure", lang),
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
            name=t("trace.private_expenditure", lang),
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

    narrative = public_private_narrative(merged, country, lang=lang)
    return fig, narrative


def outcome_measure(country, lang="en"):
    return t("narrative.education_outcome_measure", lang, country=country)


def outcome_narrative(outcome_df, pov_df, expenditure_df, country, currency_code, lang="en"):
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
    Input('stored-basic-country-data', 'data'),
    Input("stored-language", "data"),
)
def render_education_outcome(outcome_data, total_data, country, basic_country_data, lang):
    lang = lang or "en"
    if not total_data or not outcome_data:
        return dash.no_update, dash.no_update, dash.no_update

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
            name=t("trace.attendance_rate", lang),
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
            name=t("trace.learning_poverty", lang),
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
            name=t("trace.inflation_adjusted_per_capita", lang),
            x=pub_exp.year,
            y=pub_exp.per_capita_real_expenditure,
            mode="lines",
            marker_color="darkblue",
            opacity=0.6,
            customdata=np.column_stack([pub_exp.per_capita_real_expenditure_formatted]),
            hovertemplate=t("hover.inflation_adjusted_per_capita", lang) + ": %{customdata[0]}<extra></extra>",
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
            text=t("chart.education_outcome", lang),
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

    measure = outcome_measure(country, lang=lang)
    narrative = outcome_narrative(indicator, learning_poverty, pub_exp, country, currency_code, lang=lang)
    return fig, measure, narrative


@callback(
    [
        Output("econ-breakdown-func-edu", "figure"),
        Output("econ-breakdown-func-narrative-edu", "children"),
        Input("stored-data-func-econ", "data"),
        Input("country-select", "value"),
        Input("page-selector", "data"),
        Input("stored-language", "data"),
    ],
)
def render_operational_vs_capital_breakdown(data, country_name, page_func, lang):
    lang = lang or "en"
    return render_econ_breakdown(data, country_name, page_func, lang=lang)


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
    Input('stored-basic-country-data', 'data'),
    Input("stored-language", "data"),
)
def render_education_subnat_overview(func_econ_data, sub_func_data, country, selected_year, country_data, lang):
    lang = lang or "en"
    currency_code = country_data['basic_country_info'][country]['currency_code']
    return render_func_subnat_overview(
        func_econ_data, sub_func_data, country, selected_year, 'Education', currency_code, lang=lang
    )


@callback(
    Output("education-subnational-motivation", "children"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
    Input("stored-language", "data"),
)
def update_education_subnational_motivation_narrative(country_name, year, lang):
    lang = lang or "en"
    return t("narrative.edu_subnational_motivation", lang, country=country_name, year=year)


@callback(
    Output("education-expenditure-map", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
    Input("education-expenditure-type", "value"),
    Input("stored-data-subnat-boundaries", "data"),
    Input("stored-language", "data"),
    State("theme-store", "data"),
)
def update_education_expenditure_map(
    subnational_data, country_data, country, year, expenditure_type, subnat_boundaries, lang, theme
):
    lang = lang or "en"
    return update_func_expenditure_map(
        subnational_data, country_data, country, year,
        expenditure_type, subnat_boundaries, 'Education', theme=theme, lang=lang
    )


@callback(
    Output("education-outcome-map", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
    Input("stored-data-subnat-boundaries", "data"),
    Input("stored-language", "data"),
    State("theme-store", "data"),
)
def update_education_index_map(
    subnational_data, country_data, country, year, subnat_boundaries, lang, theme
):
    lang = lang or "en"
    return update_hd_index_map(
        subnational_data, country_data, country, year, subnat_boundaries, 'Education', theme=theme, lang=lang
    )


@callback(
    Output("education-subnational", "figure"),
    Output("education-subnational-narrative", "children"),
    Input("stored-data-subnational", "data"),
    Input("country-select", "value"),
    Input("year-slider-edu", "value"),
    Input('stored-basic-country-data', 'data'),
    Input("stored-language", "data"),
)
def render_education_subnat_rank(subnational_data, country, base_year, country_data, lang):
    lang = lang or "en"
    currency_code = country_data['basic_country_info'][country]['currency_code']
    return render_func_subnat_rank(subnational_data, country, base_year, 'Education', currency_code, lang=lang)
