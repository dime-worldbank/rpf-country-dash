import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from constants import get_map_disclaimer, translate_econ, START_YEAR
from translations import t, genitive, preposition, _LANGUAGES
from viz_theme import CENTRAL_COLOR, REGIONAL_COLOR, QUALITATIVE
from queries import QueryService
import server_store
from utils import (
    add_currency_column,
    apply_locale,
    empty_plot,
    filter_country_sort_year,
    format_currency,
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

# Inline funnel (filter) icon as a data URI — no icon font is loaded, so this
# keeps the "this is a filter" affordance self-contained.
import urllib.parse as _urllib_parse
_FILTER_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' "
    "fill='#495057' viewBox='0 0 16 16'>"
    "<path d='M1.5 1.5A.5.5 0 0 1 2 1h12a.5.5 0 0 1 .5.5v2a.5.5 0 0 1-.128.334"
    "L10 8.692V13.5a.5.5 0 0 1-.342.474l-3 1A.5.5 0 0 1 6 14.5V8.692L1.628 "
    "3.834A.5.5 0 0 1 1.5 3.5z'/></svg>"
)
_FILTER_ICON = "data:image/svg+xml," + _urllib_parse.quote(_FILTER_SVG)


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
        server_store.get("edu_public_expenditure")
        return {"ready": True}
    return dash.no_update


@callback(
    Output("stored-data-education-outcome", "data"),
    Input("stored-data-education-outcome", "data"),
    Input("stored-data", "data"),
)
def fetch_edu_outcome_data_once(edu_data, shared_data):
    if edu_data is None and shared_data:
        server_store.get("learning_poverty")
        server_store.get("hd_index")
        return {"ready": True}
    return dash.no_update


@callback(
    Output("stored-data-education-private", "data"),
    Input("stored-data-education-private", "data"),
)
def fetch_edu_private_data_once(edu_data):
    if edu_data is None:
        server_store.get("edu_private_expenditure")
        return {"ready": True}
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
                                dbc.Col(id="econ-breakdown-func-narrative-edu", xs=12, lg=6),
                                dbc.Col(
                                    chart_container("econ-breakdown-func-edu"),
                                    xs=12, lg=6
                                ),
                            ]
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
                        html.H3(children=t("heading.edu_func_sub_econ", lang))
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                # Economic-category filter, above the spending chart.
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Img(
                                                    src=_FILTER_ICON,
                                                    className="edu-filter-icon",
                                                    alt="",
                                                ),
                                                dbc.Label(
                                                    t("label.economic_category", lang),
                                                    html_for="education-func-sub-econ-filter",
                                                    className="edu-filter-label mb-0",
                                                ),
                                            ],
                                            className="edu-filter-label-row",
                                        ),
                                        dbc.Select(
                                            id="education-func-sub-econ-filter",
                                            size="sm",
                                            className="econ-filter-select",
                                            value="Capital expenditures",
                                            options=[
                                                {
                                                    "label": t("dropdown.all_econ_categories", lang),
                                                    "value": "__all__",
                                                }
                                            ],
                                        ),
                                    ],
                                    className="edu-filter-box",
                                ),
                                chart_container("education-func-sub-econ"),
                                # Outcome-indicator filter, above the outcome chart.
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Img(
                                                    src=_FILTER_ICON,
                                                    className="edu-filter-icon",
                                                    alt="",
                                                ),
                                                dbc.Label(
                                                    t("label.outcome_indicator", lang),
                                                    html_for="education-outcome-indicator",
                                                    className="edu-filter-label mb-0",
                                                ),
                                            ],
                                            className="edu-filter-label-row",
                                        ),
                                        dbc.Select(
                                            id="education-outcome-indicator",
                                            size="sm",
                                            className="econ-filter-select",
                                            value="completion_rate",
                                            options=[
                                                {"label": t("outcome.completion_rate", lang), "value": "completion_rate"},
                                                {"label": t("outcome.teacher_salary", lang), "value": "teacher_salary"},
                                                {"label": t("outcome.electricity", lang), "value": "electricity"},
                                                {"label": t("outcome.internet", lang), "value": "internet"},
                                            ],
                                        ),
                                    ],
                                    className="edu-filter-box",
                                ),
                                chart_container("education-level-outcome"),
                            ],
                            xs=12, lg=6,
                        ),
                        dbc.Col(
                            html.P(
                                id="education-func-sub-narrative",
                                children=t("loading", lang),
                            ),
                            xs=12, lg=6,
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
                            xs=12, lg=5
                        ),
                        dbc.Col(
                            chart_container("education-sub-func"),
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
                                        "label": t("radio.per_capita_expenditure", lang, sector_prep=preposition(lang, _LANGUAGES[lang].get("sector.education"))),
                                        "value": "per_capita_expenditure",
                                    },
                                    {
                                        "label": t("radio.total_expenditure", lang, sector_prep=preposition(lang, _LANGUAGES[lang].get("sector.education"))),
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
    add_currency_column(df, 'central_expenditure', currency_code, lang=lang)
    add_currency_column(df, 'decentralized_expenditure', currency_code, lang=lang)
    add_currency_column(df, 'real_expenditure', currency_code, lang=lang)
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

    return apply_locale(fig, lang)


def education_narrative(data, country, lang="en"):
    spending = server_store.get("edu_public_expenditure")
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
    sector_name = t("sector.education", lang)
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
    Output("education-total", "figure"),
    Output("education-narrative", "children"),
    Input("stored-data-education-total", "data"),
    Input('stored-basic-country-data', 'data'),
    Input("country-select", "value"),
    Input("stored-language", "data"),
)
def render_overview_total_figure(data, basic_country_data, country, lang):
    lang = lang or "en"
    if not data or not basic_country_data or not country:
        return dash.no_update, dash.no_update

    all_countries = server_store.get("edu_public_expenditure")
    df = filter_country_sort_year(all_countries, country)
    basic_info = server_store.get("basic_country_info")[country]
    currency_code = basic_info['currency_code']

    if df.empty:
        return (
            empty_plot(t("error.no_data_period", lang)),
            t("error.data_unavailable", lang),
        )

    fig = total_edu_figure(df, currency_code, lang=lang)
    return fig, education_narrative(data, country, lang=lang)


# Canonical education levels shared by the spending-breakdown and outcome
# charts. Both charts label and color their legend entries from this single
# model, so the same level reads identically (same wording, same color) in
# both legends. Order is pedagogical (early → late).
_LEVEL_ORDER = [
    "pre_primary",
    "primary",
    "primary_secondary",
    "lower_secondary",
    "secondary",
    "upper_secondary",
    "post_secondary",
    "tertiary",
]
# Colors come from the QUALITATIVE palette (ColorBrewer Paired), whose
# light/dark hue pairs are assigned to follow the education progression:
# blue family for primary-and-earlier, green for secondary, orange for
# post-secondary/tertiary. Levels that never share a chart may reuse a shade.
_LEVEL_COLORS = {
    "pre_primary":       QUALITATIVE[0],  # light blue
    "primary":           QUALITATIVE[1],  # blue
    "primary_secondary": QUALITATIVE[2],  # light green
    "lower_secondary":   QUALITATIVE[2],  # light green
    "secondary":         QUALITATIVE[3],  # green
    "upper_secondary":   QUALITATIVE[3],  # green
    "post_secondary":    QUALITATIVE[6],  # light orange
    "tertiary":          QUALITATIVE[7],  # orange
}

# Shared legend/margin so both charts' legend boxes match in placement & style.
_LEGEND_STYLE = dict(
    orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5,
    font=dict(size=11),
)
_CHART_MARGIN = dict(l=20, r=20, t=50, b=80)

# Education levels shown in the sub-function chart, in display order. Any
# func_sub value outside this list (nulls, mis-tagged rows like "Roads") is
# ignored. Not every country reports every level. Each is mapped to a
# canonical level so its legend entry matches the outcome chart.
EDU_FUNC_SUB_ORDER = [
    "Primary Education",
    "Primary and Secondary education",
    "Secondary Education",
    "Post-Secondary Non-Tertiary Education",
    "Tertiary Education",
]
_FUNC_SUB_TO_LEVEL = {
    "Primary Education": "primary",
    "Primary and Secondary education": "primary_secondary",
    "Secondary Education": "secondary",
    "Post-Secondary Non-Tertiary Education": "post_secondary",
    "Tertiary Education": "tertiary",
}


def _year_axis_ticks(years):
    """Return (tick0, dtick) that keep year-axis ticks on whole years.

    A plain linear axis with few points lets Plotly pick a fractional dtick
    (e.g. 0.5), which ``tickformat="d"`` then rounds to repeated year labels.
    Forcing an integer dtick (~10 ticks max) avoids the duplicates.
    """
    years = [int(y) for y in years]
    if not years:
        return 0, 1
    span = max(years) - min(years)
    dtick = max(1, round(span / 10)) if span else 1
    return min(years), dtick


def _shared_year_range(country, econ_filter):
    """[min, max] year range for the x-axis, derived from the spending
    (breakdown) data only, floored at START_YEAR. Both charts use it so they
    share one x-axis — and, crucially, the outcome indicator does NOT influence
    it, so switching indicators never moves the spending chart. Returns None
    if there's no spending data.
    """
    breakdown = server_store.get("edu_func_sub_econ_expenditure")
    breakdown = breakdown[
        (breakdown["country_name"] == country)
        & (breakdown["func_sub"].isin(EDU_FUNC_SUB_ORDER))
    ]
    if econ_filter and econ_filter != "__all__":
        breakdown = breakdown[breakdown["econ"] == econ_filter]

    years = breakdown["year"].tolist()
    if not years:
        return None
    years = [int(y) for y in years]
    return max(min(years), START_YEAR), max(years)


@callback(
    Output("education-func-sub-econ-filter", "options"),
    Output("education-func-sub-econ-filter", "value"),
    Input("country-select", "value"),
    Input("stored-language", "data"),
    State("education-func-sub-econ-filter", "value"),
)
def update_edu_func_sub_econ_options(country, lang, current_value):
    lang = lang or "en"
    options = [
        {"label": t("dropdown.all_econ_categories", lang), "value": "__all__"}
    ]
    if country:
        df = server_store.get("edu_func_sub_econ_expenditure")
        econ_values = sorted(
            df[df["country_name"] == country]["econ"].dropna().unique()
        )
        options += [
            {"label": translate_econ(e, lang), "value": e} for e in econ_values
        ]
    valid_values = {opt["value"] for opt in options}
    if current_value in valid_values:
        value = current_value
    elif "Capital expenditures" in valid_values:
        value = "Capital expenditures"
    else:
        value = "__all__"
    return options, value


# Each economic category has a natural default outcome indicator. Selecting a
# category updates the outcome dropdown; the reverse is deliberately NOT wired,
# so picking a different outcome indicator leaves the economic category alone.
_ECON_DEFAULT_OUTCOME = {
    "Wage bill": "teacher_salary",
    "Capital expenditures": "electricity",
    "Goods and services": "internet",
}


@callback(
    Output("education-outcome-indicator", "value"),
    Input("education-func-sub-econ-filter", "value"),
)
def default_outcome_for_econ(econ_filter):
    return _ECON_DEFAULT_OUTCOME.get(econ_filter, "completion_rate")


@callback(
    Output("education-func-sub-econ", "figure"),
    Input("country-select", "value"),
    Input("education-func-sub-econ-filter", "value"),
    Input("stored-basic-country-data", "data"),
    Input("stored-language", "data"),
)
def render_edu_func_sub_econ(country, econ_filter, basic_country_data, lang):
    lang = lang or "en"
    if not country:
        return empty_plot(t("loading", lang))

    df = server_store.get("edu_func_sub_econ_expenditure")
    df = df[df["country_name"] == country].copy()
    df = df[df["func_sub"].isin(EDU_FUNC_SUB_ORDER)]
    if econ_filter and econ_filter != "__all__":
        df = df[df["econ"] == econ_filter]
    if df.empty:
        return empty_plot(t("error.no_data_period", lang))

    grouped = (
        df.groupby(["func_sub", "year"], as_index=False)["per_capita_real_expenditure"]
        .sum()
        .sort_values("year")
        .rename(columns={"per_capita_real_expenditure": "value"})
    )

    currency_name = None
    currency_code = None
    if basic_country_data:
        info = server_store.get("basic_country_info").get(country, {})
        currency_name = info.get("currency_name")
        currency_code = info.get("currency_code")

    # Fixed display order; skip levels this country/filter doesn't report.
    present = set(grouped["func_sub"].unique())
    ordered = [f for f in EDU_FUNC_SUB_ORDER if f in present]

    fig = go.Figure()
    for func_sub in ordered:
        # Drop 0/missing values — they mean unreported spending (or no
        # population), not a real zero, so the line skips those years.
        sub = grouped[
            (grouped["func_sub"] == func_sub)
            & grouped["value"].notna()
            & (grouped["value"] != 0)
        ]
        if sub.empty:
            continue
        level = _FUNC_SUB_TO_LEVEL[func_sub]
        label = t(f"level.{level}", lang)
        color = _LEVEL_COLORS.get(level)
        if currency_code:
            formatted = sub["value"].apply(
                lambda v: format_currency(v, currency_code, lang=lang)
            )
            customdata = np.column_stack([formatted])
            hovertemplate = f"<b>{label}</b>: %{{customdata[0]}}<extra></extra>"
        else:
            customdata = None
            hovertemplate = f"<b>{label}</b>: %{{y}}<extra></extra>"
        fig.add_trace(
            go.Scatter(
                name=label,
                x=sub["year"],
                y=sub["value"],
                mode="lines+markers",
                line=dict(color=color),
                marker=dict(color=color),
                customdata=customdata,
                hovertemplate=hovertemplate,
            )
        )

    year_range = _shared_year_range(country, econ_filter)
    if year_range:
        lo, hi = year_range
        tick0, dtick = _year_axis_ticks([lo, hi])
        fig.update_xaxes(
            tickformat="d", tick0=tick0, dtick=dtick, range=[lo - 0.5, hi + 0.5]
        )
    else:
        fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    if currency_name:
        fig.update_yaxes(
            title_text=t("axis.per_capita_real_expenditure", lang, currency_name=currency_name)
        )
    fig.update_layout(
        hovermode="x unified",
        title=t("chart.edu_func_sub_econ", lang),
        plot_bgcolor="white",
        legend=_LEGEND_STYLE,
        margin=_CHART_MARGIN,
    )
    return apply_locale(fig, lang)


@callback(
    Output("education-func-sub-narrative", "children"),
    Input("country-select", "value"),
    Input("education-func-sub-econ-filter", "value"),
    Input("stored-language", "data"),
)
def render_edu_func_sub_narrative(country, econ_filter, lang):
    lang = lang or "en"
    if not country:
        return t("loading", lang)

    df = server_store.get("edu_func_sub_econ_expenditure")
    df = df[
        (df["country_name"] == country)
        & (df["func_sub"].isin(EDU_FUNC_SUB_ORDER))
        & df["per_capita_real_expenditure"].notna()
        & (df["per_capita_real_expenditure"] != 0)
    ]
    if econ_filter and econ_filter != "__all__":
        df = df[df["econ"] == econ_filter]
    if df.empty:
        return t("error.no_data_period", lang)

    currency_code = (
        server_store.get("basic_country_info").get(country, {}).get("currency_code")
    )

    def _fmt(value):
        if currency_code:
            return format_currency(value, currency_code, lang=lang)
        return millify(value, lang=lang)

    # Make the selected economic category explicit (lowercased for mid-sentence).
    if econ_filter and econ_filter != "__all__":
        scope = t(
            "narrative.econ_scope_one", lang,
            econ=translate_econ(econ_filter, lang).lower(),
        )
    else:
        scope = t("narrative.econ_scope_all", lang)

    # Rank levels by average real per-capita spending over the years, so a
    # level with more years of data isn't favored over one with fewer.
    means = df.groupby("func_sub")["per_capita_real_expenditure"].mean()
    start_year, end_year = int(df["year"].min()), int(df["year"].max())
    most_key = means.idxmax()
    most_label = t(f"level.{_FUNC_SUB_TO_LEVEL[most_key]}.long", lang)

    if len(means) == 1:
        return t(
            "narrative.edu_func_sub_single", lang,
            scope=scope, level=most_label, start=start_year, end=end_year,
            level_val=_fmt(means.loc[most_key]),
        )
    least_key = means.idxmin()
    least_label = t(f"level.{_FUNC_SUB_TO_LEVEL[least_key]}.long", lang)
    return t(
        "narrative.edu_func_sub_most_least", lang,
        scope=scope, most=most_label, least=least_label,
        start=start_year, end=end_year,
        most_val=_fmt(means.loc[most_key]), least_val=_fmt(means.loc[least_key]),
    )


# Intermediate-outcome indicator shown next to the sub-function breakdown,
# selected by the econ dropdown. Each config maps education levels to the
# indicator column; any econ not listed falls back to completion rate.
_TEACHER_SALARY_OUTCOME = {
    "store_key": "teacher_salaries",
    "title_key": "chart.teacher_salary",
    "axis_key": "axis.teacher_salary",
    "value_fmt": ".2f",
    "suffix": "",
    "y_range": None,
    "columns": {
        "pre_primary": "teacher_salary_pre_primary",
        "primary": "teacher_salary_primary",
        "lower_secondary": "teacher_salary_lower_secondary",
        "upper_secondary": "teacher_salary_upper_secondary",
    },
}
_ELECTRICITY_OUTCOME = {
    "store_key": "school_basic_services",
    "title_key": "chart.schools_electricity",
    "axis_key": "axis.pct_schools",
    "value_fmt": ".1f",
    "suffix": "%",
    "y_range": [0, 100],
    "columns": {
        "primary": "schools_with_electricity_primary",
        "lower_secondary": "schools_with_electricity_lower_secondary",
        "upper_secondary": "schools_with_electricity_upper_secondary",
    },
}
_INTERNET_OUTCOME = {
    "store_key": "school_basic_services",
    "title_key": "chart.schools_internet",
    "axis_key": "axis.pct_schools",
    "value_fmt": ".1f",
    "suffix": "%",
    "y_range": [0, 100],
    "columns": {
        "primary": "schools_with_internet_primary",
        "lower_secondary": "schools_with_internet_lower_secondary",
        "upper_secondary": "schools_with_internet_upper_secondary",
    },
}
_COMPLETION_RATE_OUTCOME = {
    "store_key": "completion_rates",
    "title_key": "chart.completion_rate",
    "axis_key": "axis.completion_rate",
    "value_fmt": ".1f",
    "suffix": "%",
    "y_range": [0, 100],
    "columns": {
        "primary": "completion_rate_primary",
        "lower_secondary": "completion_rate_lower_secondary",
        "upper_secondary": "completion_rate_upper_secondary",
    },
}
# Outcome indicator the user can pick from the second dropdown.
_OUTCOME_BY_KEY = {
    "completion_rate": _COMPLETION_RATE_OUTCOME,
    "teacher_salary": _TEACHER_SALARY_OUTCOME,
    "electricity": _ELECTRICITY_OUTCOME,
    "internet": _INTERNET_OUTCOME,
}
_DEFAULT_OUTCOME_KEY = "completion_rate"


@callback(
    Output("education-level-outcome", "figure"),
    Input("country-select", "value"),
    Input("education-func-sub-econ-filter", "value"),
    Input("education-outcome-indicator", "value"),
    Input("stored-language", "data"),
)
def render_edu_level_outcome(country, econ_filter, indicator, lang):
    lang = lang or "en"
    if not country:
        return empty_plot(t("loading", lang))

    cfg = _OUTCOME_BY_KEY.get(indicator, _COMPLETION_RATE_OUTCOME)
    df = server_store.get(cfg["store_key"])
    df = df[df["country_name"] == country].sort_values("year")

    fig = go.Figure()
    for level in _LEVEL_ORDER:
        col = cfg["columns"].get(level)
        if not col or col not in df.columns:
            continue
        # Drop missing and 0 values (0 = not reported, not a real zero).
        series = df[["year", col]].dropna()
        series = series[series[col] != 0]
        if series.empty:
            continue
        label = t(f"level.{level}", lang)
        color = _LEVEL_COLORS.get(level)
        fig.add_trace(
            go.Scatter(
                name=label,
                x=series["year"],
                y=series[col],
                mode="lines+markers",
                line=dict(color=color),
                marker=dict(color=color),
                hovertemplate=f"<b>{label}</b>: %{{y:{cfg['value_fmt']}}}{cfg['suffix']}<extra></extra>",
            )
        )

    if not fig.data:
        return empty_plot(t("error.no_data_period", lang))

    year_range = _shared_year_range(country, econ_filter)
    if year_range:
        lo, hi = year_range
        tick0, dtick = _year_axis_ticks([lo, hi])
        fig.update_xaxes(
            tickformat="d", tick0=tick0, dtick=dtick, range=[lo - 0.5, hi + 0.5]
        )
    else:
        fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True, title_text=t(cfg["axis_key"], lang))
    if cfg["y_range"]:
        fig.update_yaxes(range=cfg["y_range"])
    fig.update_layout(
        hovermode="x unified",
        title=t(cfg["title_key"], lang),
        plot_bgcolor="white",
        legend=_LEGEND_STYLE,
        margin=_CHART_MARGIN,
    )
    return apply_locale(fig, lang)


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
            country_meta = _LANGUAGES[lang].get(f"country.{country}")
            sector_meta = _LANGUAGES[lang].get("sector.education")
            text += t("narrative.govt_share_trend", lang,
                       country=country_display,
                       country_loc=preposition(lang, country_meta, capitalize=True),
                       sector_prep=preposition(lang, sector_meta), trend=trend,
                       earliest_pct=f"{earliest_gov_share:.0%}",
                       latest_pct=f"{latest_gov_share:.0%}",
                       earliest_year=earliest_year, latest_year=latest_year)

        text += t("narrative.household_ratio", lang,
                   sector_prep=preposition(lang, _LANGUAGES[lang].get("sector.education")),
                   ratio=f"{household_ratio:.1f}", year=latest_year)

    except IndexError:
        return t("error.data_unavailable", lang)
    except:
        return t("error.generic", lang)
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

    currency_code = server_store.get("basic_country_info")[country]['currency_code']
    fig_title = t("chart.pct_govt_vs_household", lang)

    private = server_store.get("edu_private_expenditure")
    private = filter_country_sort_year(private, country)

    public_df = server_store.get("edu_public_expenditure")
    public = filter_country_sort_year(public_df, country)

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
            prompt = t("error.data_unavailable_named", lang,
                       dataset_name="Education public spending")
        elif private.empty:
            prompt = t("error.data_unavailable_named", lang,
                       dataset_name="Education private spending")
        else:
            prompt = t("error.no_overlapping_data", lang, sector_prep=preposition(lang, _LANGUAGES[lang].get("sector.education")))
        return (empty_plot(prompt, fig_title=fig_title), prompt)

    merged["private_percentage"] = merged["real_expenditure_private"] / (
        merged["real_expenditure_private"] + merged["real_expenditure_public"]
    )
    merged["public_percentage"] = 1 - merged["private_percentage"]

    add_currency_column(merged, 'real_expenditure_private', currency_code, lang=lang)
    add_currency_column(merged, 'real_expenditure_public', currency_code, lang=lang)
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
    return apply_locale(fig, lang), narrative


def outcome_measure(country, lang="en"):
    return t("narrative.education_outcome_measure", lang, country=t(f"country.{country}", lang))


def outcome_narrative(outcome_df, pov_df, expenditure_df, country, currency_code, lang="en"):
    exp_df = expenditure_df.dropna(subset=["per_capita_real_expenditure"])
    att_df = outcome_df.dropna(subset=["attendance_6to17yo"])
    pov_df_clean = pov_df.dropna(subset=["learning_poverty_rate"])

    spending_fmt = lambda x: format_currency(x, currency_code, lang=lang)

    attendance_result = get_relationship_narrative(
        reference_years=exp_df["year"].values,
        reference_values=exp_df["per_capita_real_expenditure"].values,
        comparison_years=att_df["year"].values,
        comparison_values=att_df["attendance_6to17yo"].values,
        reference_name=t("metric.per_capita_education_spending", lang),
        comparison_name=t("metric.school_attendance", lang),
        reference_format=spending_fmt,
        comparison_format=".1f",
        lang=lang,
    )

    poverty_result = get_relationship_narrative(
        reference_years=exp_df["year"].values,
        reference_values=exp_df["per_capita_real_expenditure"].values,
        comparison_years=pov_df_clean["year"].values,
        comparison_values=pov_df_clean["learning_poverty_rate"].values,
        reference_name=t("metric.per_capita_education_spending", lang),
        comparison_name=t("metric.learning_poverty_rate", lang),
        reference_format=spending_fmt,
        comparison_format=".1f",
        lang=lang,
    )

    both_insufficient = (
        attendance_result["method"] == "insufficient_data" and
        poverty_result["method"] == "insufficient_data"
    )
    if both_insufficient:
        return t("narrative.both_insufficient", lang)

    poverty_narrative = poverty_result["narrative"]
    poverty_narrative = poverty_narrative[0].lower() + poverty_narrative[1:]
    return f"{attendance_result['narrative']}{t('narrative.outcome_meanwhile', lang, pcc=poverty_narrative)}"


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
    if not total_data or not outcome_data or not basic_country_data or not country:
        return dash.no_update, dash.no_update, dash.no_update

    indicator = server_store.get("hd_index")
    indicator = filter_country_sort_year(indicator, country)
    indicator = indicator[indicator.adm1_name == "Total"]

    learning_poverty = server_store.get("learning_poverty")
    learning_poverty = filter_country_sort_year(learning_poverty, country)

    pub_exp = server_store.get("edu_public_expenditure")
    pub_exp = filter_country_sort_year(pub_exp, country)

    currency_code = server_store.get("basic_country_info")[country]['currency_code']

    add_currency_column(pub_exp, 'per_capita_real_expenditure', currency_code, lang=lang)
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
    return apply_locale(fig, lang), measure, narrative


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
    if not country_data or not country:
        return dash.no_update, dash.no_update, dash.no_update
    currency_code = server_store.get("basic_country_info")[country]['currency_code']
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
    return t("narrative.edu_subnational_motivation", lang,
             country=t(f"country.{country_name}", lang), year=year)


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
    if not country_data or not country:
        return empty_plot("Loading..."), "Loading..."
    currency_code = server_store.get("basic_country_info")[country]['currency_code']
    return render_func_subnat_rank(subnational_data, country, base_year, 'Education', currency_code, lang=lang)
