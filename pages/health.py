import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from constants import get_map_disclaimer
from translations import t, genitive, locative
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
                            id="health-tabs",
                            active_tab="health-tab-time",
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
    Output("health-tabs", "children"),
    Input("stored-language", "data"),
)
def update_health_tab_labels(lang):
    return [
        dbc.Tab(label=t("tab.over_time", lang), tab_id="health-tab-time"),
        dbc.Tab(label=t("tab.across_space", lang), tab_id="health-tab-space"),
    ]


@callback(
    Output("stored-data-health-total", "data"),
    Input("stored-data-health-total", "data"),
    Input("stored-data-func-econ", "data"),
)
def fetch_health_total_data_once(health_data, shared_data):
    if health_data is None and shared_data:
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
    Input("stored-language", "data"),
)
def render_health_content(tab, lang):
    lang = lang or "en"
    if tab == "health-tab-time":
        return html.Div(
            [
                dbc.Row(
                    dbc.Col(
                        html.H3(children=t("heading.who_pays_health", lang))
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="health-public-private-narrative",
                                children=t("loading", lang),
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
                            chart_container("health-public-private"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                        dbc.Col(
                            chart_container("health-total"),
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
                        html.H3(children=t("heading.public_spending_health_outcome", lang))
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            chart_container("health-outcome"),
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
                        dbc.Col(dcc.Store(id="page-selector", data="Health"), width=0),
                        dbc.Row(
                            [
                                dbc.Col(id="econ-breakdown-func-narrative-health", xs=12, lg=6),
                                dbc.Col(
                                    chart_container("econ-breakdown-func-health"),
                                    xs=12, lg=6
                                ),
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
                        html.H3(children=t("heading.central_vs_geo_health", lang))
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="health-sub-func-narrative",
                                children=t("loading", lang),
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            chart_container("health-central-vs-regional"),
                            xs=12, lg=5
                        ),
                        dbc.Col(
                            chart_container("health-sub-func"),
                            xs=12, lg=7
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
                            id="health-subnational-title",
                            children=t("heading.public_spending_health_regions", lang),
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                children=t("narrative.health_subnational_context", lang),
                            ),
                            html.P(
                                id="health-subnational-motivation",
                                children=t("loading", lang),
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
                                            "label": t("radio.per_capita_expenditure", lang, sector=t("sector.health", lang)),
                                            "value": "per_capita_expenditure",
                                        },
                                        {
                                            "label": t("radio.total_expenditure", lang, sector=t("sector.health", lang)),
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
                                disclaimer_tooltip("health-expenditure-warning", get_map_disclaimer(lang), lang=lang),
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
                            chart_container("health-expenditure-map"),
                            xs=12,
                            sm=12,
                            md=6,
                            lg=6,
                        ),
                        dbc.Col(
                            chart_container("health-outcome-map"),
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
                                children=t("loading", lang),
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            chart_container("health-subnational"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 12, "offset": 0},
                        )
                    ]
                ),
            ],
        )


def total_health_figure(df, currency_code, lang="en"):
    fig = go.Figure()

    if df is None:
        return fig
    add_currency_column(df, 'real_expenditure', currency_code)
    add_currency_column(df, 'central_expenditure', currency_code)
    add_currency_column(df, 'decentralized_expenditure', currency_code)
    fig.add_trace(
        go.Scatter(
            name=t("trace.inflation_adjusted", lang),
            customdata=df['real_expenditure_formatted'],
            x=df.year,
            y=df.real_expenditure,
            mode="lines+markers",
            marker_color="darkblue",
            hovertemplate="<b>" + t("hover.real_expenditure", lang) + "</b>: %{customdata}<extra></extra>",

        ),
    )
    fig.add_trace(
        go.Bar(
            name=t("trace.central", lang),
            customdata=df['central_expenditure_formatted'],
            x=df.year,
            y=df.central_expenditure,
            marker_color=CENTRAL_COLOR,
            hovertemplate="<b>" + t("hover.real_central_expenditure", lang) + "</b>: %{customdata}<extra></extra>",
        ),
    )
    fig.add_trace(
        go.Bar(
            name=t("trace.regional", lang),
            customdata=df['decentralized_expenditure_formatted'],
            x=df.year,
            y=df.decentralized_expenditure,
            marker_color=REGIONAL_COLOR,
            hovertemplate="<b>" + t("hover.real_decentralized_expenditure", lang) + "</b>: %{customdata}<extra></extra>",
        ),
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        barmode="stack",
        hovermode="x unified",
        title=t("chart.health_spending_over_time", lang),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1),
    )

    return fig


def health_narrative(data, country, lang="en"):
    spending = pd.DataFrame(data["health_public_expenditure"])
    spending = filter_country_sort_year(spending, country)

    plot_df = (
        spending.dropna(subset=["real_expenditure"])
        .groupby("year")["real_expenditure"].sum()
        .reset_index()
        .sort_values("year")
    )
    extractor = InsightExtractor(plot_df["year"].values, plot_df["real_expenditure"].values)
    trend_narrative = get_segment_narrative(extractor=extractor, metric=t("metric.real_expenditure", lang), lang=lang)

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
    sector_name = t("sector.health", lang)
    sector_gen = genitive(lang, sector_name)
    if pd.isna(decentralization) or decentralization == 0:
        spending_decentralization = t(
            "narrative.decentralization_unknown", lang,
            sector=sector_name, sector_gen=sector_gen,
        )
    else:
        spending_decentralization = t(
            "narrative.decentralization_by_year", lang,
            year=end_year, pct=f"{decentralization:.1%}",
            sector=sector_name, sector_gen=sector_gen,
        )
    text += spending_decentralization

    return text


@callback(
    Output("health-total", "figure"),
    Output("health-narrative", "children"),
    Input("stored-data-health-total", "data"),
    Input("country-select", "value"),
    Input("stored-basic-country-data", "data"),
    Input("stored-language", "data"),
)
def render_overview_total_figure(data, country, country_data, lang):
    lang = lang or "en"
    if not data or not country_data:
        return dash.no_update, dash.no_update

    all_countries = pd.DataFrame(data["health_public_expenditure"])
    df = filter_country_sort_year(all_countries, country)

    if df.empty:
        return (
            empty_plot(t("error.no_data_period", lang)),
            generate_error_prompt("DATA_UNAVAILABLE", lang=lang),
        )
    currency_code = country_data['basic_country_info'][country]['currency_code']

    fig = total_health_figure(df, currency_code, lang=lang)
    return fig, health_narrative(data, country, lang=lang)


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
            country_display = t(f"country.{country}", lang)
            text += t("narrative.govt_share_trend", lang,
                       country=country_display,
                       country_loc=locative(lang, country_display),
                       sector=t("sector.health", lang), trend=trend,
                       earliest_pct=f"{earliest_gov_share:.0%}",
                       latest_pct=f"{latest_gov_share:.0%}",
                       earliest_year=earliest_year, latest_year=latest_year)

        text += t("narrative.household_ratio", lang, sector=t("sector.health", lang),
                   ratio=f"{household_ratio:.1f}", year=latest_year)

    except IndexError:
        return generate_error_prompt("DATA_UNAVAILABLE", lang=lang)
    except:
        return generate_error_prompt("GENERIC_ERROR", lang=lang)
    return text


@callback(
    Output("health-public-private", "figure"),
    Output("health-public-private-narrative", "children"),
    Input("stored-data-health-private", "data"),
    Input("stored-data-health-total", "data"),
    Input("country-select", "value"),
    Input("stored-basic-country-data", "data"),
    Input("stored-language", "data"),
)
def render_public_private_figure(private_data, public_data, country, country_data, lang):
    lang = lang or "en"
    if not private_data or not public_data:
        return dash.no_update, dash.no_update

    fig_title = t("chart.pct_govt_vs_household", lang)
    currency_code = country_data['basic_country_info'][country]['currency_code']

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
                "DATA_UNAVAILABLE_DATASET_NAME", lang=lang, dataset_name="health public spending"
            )
        elif private.empty:
            prompt = generate_error_prompt(
                "DATA_UNAVAILABLE_DATASET_NAME", lang=lang, dataset_name="health private spending"
            )
        else:
            prompt = t("error.no_overlapping_data", lang, sector=t("sector.health", lang))
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
            hovertemplate="<b>" + t("hover.real_public_expenditure", lang) + "</b>: %{customdata}<extra></extra>",
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
            hovertemplate="<b>" + t("hover.real_private_expenditure", lang) + "</b>: %{customdata}<extra></extra>",
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


def outcome_measure(lang="en"):
    return t("narrative.health_outcome_measure", lang)


def outcome_narrative(outcome_df, expenditure_df, country, currency_code, lang="en"):
    exp_df = expenditure_df.dropna(subset=["per_capita_real_expenditure"])
    out_df = outcome_df.dropna(subset=["universal_health_coverage_index"])

    result = get_relationship_narrative(
        reference_years=exp_df["year"].values,
        reference_values=exp_df["per_capita_real_expenditure"].values,
        comparison_years=out_df["year"].values,
        comparison_values=out_df["universal_health_coverage_index"].values,
        reference_name=t("metric.per_capita_health_spending", lang),
        comparison_name=t("metric.uhc_index", lang),
        reference_format=lambda x: format_currency(x, currency_code),
        comparison_format=".1f",
        lang=lang,
    )
    return result["narrative"]


@callback(
    Output("health-outcome", "figure"),
    Output("health-outcome-measure", "children"),
    Output("health-outcome-narrative", "children"),
    Input("stored-data-health-outcome", "data"),
    Input("stored-data-health-total", "data"),
    Input("country-select", "value"),
    Input("stored-basic-country-data", "data"),
    Input("stored-language", "data"),
)
def render_health_outcome(outcome_data, total_data, country, country_data, lang):
    lang = lang or "en"
    if not total_data or not outcome_data:
        return dash.no_update, dash.no_update, dash.no_update

    uhc = pd.DataFrame(outcome_data["uhc_index"])
    uhc = filter_country_sort_year(uhc, country)

    pub_exp = pd.DataFrame(total_data["health_public_expenditure"])
    pub_exp = filter_country_sort_year(pub_exp, country)
    currency_code = country_data['basic_country_info'][country]['currency_code']
    add_currency_column(pub_exp, 'per_capita_real_expenditure', currency_code)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            name=t("trace.uhc_index", lang),
            x=uhc.year,
            y=uhc.universal_health_coverage_index,
            mode="lines+markers",
            line=dict(color="deeppink", shape="spline", dash="dot"),
            connectgaps=True,
            hovertemplate="UHC Index: %{y:.1f}<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            name=t("trace.inflation_adjusted_per_capita_health", lang),
            customdata=pub_exp['per_capita_real_expenditure_formatted'],
            x=pub_exp.year,
            y=pub_exp.per_capita_real_expenditure,
            mode="lines",
            marker_color="darkblue",
            opacity=0.6,
            hovertemplate=t("hover.inflation_adjusted_per_capita", lang) + ": %{customdata}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.update_layout(
        plot_bgcolor="white",
        hovermode="x unified",
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
            text=t("chart.health_outcome", lang),
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
    fig.update_yaxes(range=[0, 120], secondary_y=True)

    narrative = outcome_narrative(uhc, pub_exp, country, currency_code, lang=lang)
    return fig, outcome_measure(lang=lang), narrative


@callback(
    [
        Output("econ-breakdown-func-health", "figure"),
        Output("econ-breakdown-func-narrative-health", "children"),
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
    Input("stored-basic-country-data", "data"),
    Input("stored-language", "data"),
)
def render_health_subnat_overview(func_data, sub_func_data, country, selected_year, country_data, lang):
    lang = lang or "en"
    currency_code = country_data['basic_country_info'][country]['currency_code']
    return render_func_subnat_overview(
        func_data, sub_func_data, country, selected_year, 'Health', currency_code, lang=lang
    )

@callback(
    Output("health-subnational-motivation", "children"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
    Input("stored-language", "data"),
)
def update_health_subnational_motivation_narrative(country_name, year, lang):
    lang = lang or "en"
    return t("narrative.health_subnational_motivation", lang,
             country=t(f"country.{country_name}", lang), year=year)


@callback(
    Output("health-expenditure-map", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
    Input("health-expenditure-type", "value"),
    Input("stored-data-subnat-boundaries", "data"),
    Input("stored-language", "data"),
    State("theme-store", "data"),
)
def update_health_expenditure_map(
    subnational_data, country_data, country, year, expenditure_type, subnat_boundaries, lang, theme
):
    lang = lang or "en"
    return update_func_expenditure_map(
        subnational_data, country_data, country, year,
        expenditure_type, subnat_boundaries, 'Health', theme=theme, lang=lang
    )


@callback(
    Output("health-outcome-map", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
    Input("stored-data-subnat-boundaries", "data"),
    Input("stored-language", "data"),
    State("theme-store", "data"),
)
def update_health_index_map(
    subnational_data, country_data, country, year, subnat_boundaries, lang, theme
):
    lang = lang or "en"
    return update_hd_index_map(
        subnational_data, country_data, country, year, subnat_boundaries, 'Health', theme=theme, lang=lang
    )


@callback(
    Output("health-subnational", "figure"),
    Output("health-subnational-narrative", "children"),
    Input("stored-data-subnational", "data"),
    Input("country-select", "value"),
    Input("year-slider-health", "value"),
    Input("stored-basic-country-data", "data"),
    Input("stored-language", "data"),
)
def render_health_subnat_rank(subnational_data, country, base_year, country_data, lang):
    lang = lang or "en"
    currency_code = country_data['basic_country_info'][country]['currency_code']
    return render_func_subnat_rank(subnational_data, country, base_year, 'Health', currency_code, lang=lang)
