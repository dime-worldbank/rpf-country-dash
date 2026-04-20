import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils import add_disputed_overlay
from plotly.subplots import make_subplots
import numpy as np
from utils import (
    add_currency_column,
    filter_country_sort_year,
    filter_geojson_by_country,
    empty_plot,
    get_correlation_text,
    remove_accents,
    require_login,
    format_currency_yaxis,
    format_currency,
    millify
)

from components import slider, get_slider_config, pefa, budget_increment_analysis
from trend_narrative import get_segment_narrative, InsightExtractor
from components.disclaimer_div import disclaimer_tooltip
from components.source_metadata_popover import chart_container, empty_modal
from constants import COFOG_CATS, COFOG_KEY_MAP, FUNC_COLORS, get_map_disclaimer
from translations import t, genitive
from viz_theme import QUALITATIVE_ALT, get_map_colorscale, CENTRAL_COLOR, REGIONAL_COLOR
from queries import QueryService


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
                            id="overview-tabs",
                            active_tab="overview-tab-time",
                            style={"marginBottom": "2rem"},
                        ),
                        html.Div(id="overview-content"),
                    ]
                )
            ),
            dcc.Store(id="stored-data-pefa"),
        ]
    )


@callback(
    Output("overview-tabs", "children"),
    Input("stored-language", "data"),
)
def update_overview_tab_labels(lang):
    return [
        dbc.Tab(label=t("tab.over_time", lang), tab_id="overview-tab-time"),
        dbc.Tab(label=t("tab.across_space", lang), tab_id="overview-tab-space"),
    ]


@callback(
    Output("stored-data-pefa", "data"),
    Input("stored-data-pefa", "data"),
    Input("stored-data", "data"),
)
def fetch_pefa_data_once(pefa_data, shared_data):
    if pefa_data is None and shared_data:
        pefa_df = db.get_pefa(shared_data["countries"])
        return {
            "pefa": pefa_df.to_dict("records"),
        }
    return dash.no_update

@callback(
    Output("overview-content", "children"),
    Input("overview-tabs", "active_tab"),
    Input("stored-language", "data"),
)
def render_overview_content(tab, lang):
    lang = lang or "en"
    if tab == "overview-tab-time":
        return html.Div(
            [
                dbc.Row(
                    dbc.Col(
                        html.H3(children=t("heading.total_expenditure", lang))
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.P(
                            id="overview-narrative",
                            children=t("loading", lang),
                        )
                    )
                ),
                dbc.Row(
                    [
                        # How has total expenditure changed over time?
                        dbc.Col(
                            chart_container("overview-total"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                        # How has per capita expenditure changed over time?
                        dbc.Col(
                            chart_container("overview-per-capita"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                    ],
                ),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.H3(children=t("heading.spending_by_func", lang))
                    )
                ),
                dbc.Row(
                    [
                        # How has sector prioritization changed over time?
                        dbc.Col(
                            chart_container("functional-breakdown"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 8, "offset": 0},
                        ),
                        dbc.Col(
                            html.P(
                                id="functional-narrative",
                                children=t("loading", lang),
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 4, "offset": 0},
                        ),
                    ],
                ),
                dbc.Row(style={"height": "40px"}),
                dbc.Row(
                    [
                        dbc.Col([
                            html.P(
                                id="func-growth-narrative",
                                children=t("loading", lang),
                            ),
                            html.P(
                                id="func-growth-instruction",
                                children=html.Small(html.Em(t("instruction.budget_legend", lang))),
                            )
                        ], xs=12, lg=4),
                        dbc.Col([
                            html.Div([
                                dbc.RadioItems(
                                    id="budget-increment-radio",
                                    options=[
                                        {
                                            "label": t("radio.budget", lang),
                                            "value": "domestic_funded_budget",
                                        },
                                        {
                                            "label": t("radio.inflation_adjusted_budget", lang),
                                            "value": "real_domestic_funded_budget",
                                        },
                                    ],
                                    value="domestic_funded_budget",
                                    inline=True,
                                    style={"padding": "10px"},
                                    labelStyle={"margin-right": "20px"},
                                )
                            ], className='disclaimer-div'),
                            chart_container("func-growth"),
                        ], xs=12, lg=8),
                    ]
                ),
                dbc.Row(style={"height": "20px"}),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.H3(children=t("heading.spending_by_econ", lang))
                    )
                ),
                dbc.Row(
                    [
                        # How much was spent on each economic category?
                        dbc.Col(
                            chart_container("economic-breakdown"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 8, "offset": 0},
                        ),
                        dbc.Col(
                            html.P(
                                id="economic-narrative",
                                children=t("loading", lang),
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 4, "offset": 0},
                        ),
                    ],
                ),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.H3(children=t("heading.quality_budget", lang))
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.P(
                            id="pefa-narrative",
                            children=t("loading", lang),
                        ),
                    ),
                ),
                dbc.Row(
                    [
                        # How did the overall quality of budget institutions change over time?
                        dbc.Col(
                            chart_container("pefa-overall"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 5, "offset": 0},
                        ),
                        # How did various pillars of the budget institutions change over time?
                        dbc.Col(
                            chart_container("pefa-by-pillar"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 7, "offset": 0},
                        ),
                    ],
                ),
            ]
        )
    elif tab == "overview-tab-space":
        return html.Div(
            [
                dbc.Row(
                    dbc.Col(
                        html.H3(
                            id="regional-expenditure-heading",
                            children=t("heading.regional_expenditure", lang),
                        )
                    )
                ),
                dbc.Row(style={"height": "20px"}),
                # "Geospatial choropleths"
                dbc.Row(
                    [
                        dbc.Col(width=1),
                        dbc.Col(
                            slider("year-slider", "year-slider-container"),
                            width=10,
                        ),
                    ]
                ),
                dbc.Row(style={"height": "20px"}),
                dbc.Row(
                    [
                        html.Div(
                            [
                                dbc.RadioItems(
                                    id="expenditure-plot-radio",
                                    options=[
                                        {
                                            "label": t("radio.per_capita_expenditure_plain", lang),
                                            "value": "percapita",
                                        },
                                        {
                                            "label": t("radio.total_expenditure_plain", lang),
                                            "value": "total",
                                        },
                                    ],
                                    value="percapita",
                                    inline=True,
                                    style={"padding": "10px"},
                                    labelStyle={
                                        "margin-right": "20px",
                                    },
                                ),
                                disclaimer_tooltip("warning-sign", get_map_disclaimer(lang), lang=lang),
                            ],
                            className="disclaimer-div",
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "space-between",
                                "width": "100%",
                            },
                        ),
                        # How much was spent in each region?
                        dbc.Col(
                            chart_container("subnational-spending"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                        # visualization of poverty by region
                        dbc.Col(
                            chart_container("subnational-poverty"),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                    ],
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.Br(),
                            html.P(
                                id="subnational-spending-narrative",
                                children=t("loading", lang),
                            ),
                        ]
                    )
                ),
                html.Div(style={"height": "20px"}),
            ]
        )


def total_figure(df, currency_name, currency_code, lang="en"):
    fig = go.Figure()
    add_currency_column(df, 'real_expenditure', currency_code)
    df['central_expenditure_formatted'] = (df['expenditure'] - df['decentralized_expenditure']).apply(lambda x: format_currency(x, currency_code))
    add_currency_column(df, 'decentralized_expenditure', currency_code)
    fig.add_trace(
        go.Scatter(
            name=t("trace.inflation_adjusted", lang),
            x=df.year,
            y=df.real_expenditure,
            mode="lines+markers",
            marker_color="darkblue",
            customdata=np.column_stack([df['real_expenditure_formatted']]),
            hovertemplate=t("hover.inflation_adjusted_expenditure", lang) + ": %{customdata[0]}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name=t("trace.central", lang),
            x=df.year,
            y=df.expenditure - df.decentralized_expenditure,
            marker_color=CENTRAL_COLOR,
            customdata=np.column_stack([df['central_expenditure_formatted']]),
            hovertemplate=t("hover.central_expenditure", lang) + ": %{customdata[0]}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name=t("trace.regional", lang),
            x=df.year,
            y=df.decentralized_expenditure,
            marker_color=REGIONAL_COLOR,
            customdata=np.column_stack([df['decentralized_expenditure_formatted']]),
            hovertemplate=t("hover.regional_expenditure", lang) + ": %{customdata[0]}<extra></extra>",
        )
    )

    format_currency_yaxis(fig, currency_name, t("axis.total_expenditure", lang))
    fig.update_layout(
        barmode="stack",
        title=t("chart.total_expenditure_over_time", lang),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
        hovermode="x unified",
    )

    return fig


def per_capita_figure(df, currency_name, currency_code, lang="en"):
    add_currency_column(df, 'per_capita_expenditure', currency_code)
    add_currency_column(df, 'per_capita_real_expenditure', currency_code)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            name=t("trace.poverty_rate", lang),
            x=df.year,
            y=df.poverty_rate,
            mode="lines+markers",
            line=dict(color="darkred", shape="spline", dash="dot"),
            connectgaps=True,
            hovertemplate=("%{x}: %{y:.2f}%"),
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            name=t("trace.inflation_adjusted", lang),
            x=df.year,
            y=df.per_capita_real_expenditure,
            mode="lines+markers",
            marker_color="darkblue",
            customdata=np.column_stack([df['per_capita_real_expenditure_formatted']]),
            hovertemplate=t("hover.inflation_adjusted_per_capita", lang) + ": %{customdata[0]}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            name=t("trace.per_capita", lang),
            x=df.year,
            y=df.per_capita_expenditure,
            marker_color="#686dc3",
            customdata=np.column_stack([df['per_capita_expenditure_formatted']]),
            hovertemplate=t("hover.per_capita_spending", lang) + ": %{customdata[0]}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(title_text=t("axis.per_capita_expenditure", lang, currency_name=currency_name), secondary_y=False, fixedrange=True)
    fig.update_yaxes(
        title_text=t("axis.poverty_rate", lang),
        secondary_y=True,
        range=[-1, 100],
    )
    fig.update_layout(
        hovermode="x unified",
        barmode="stack",
        title=t("chart.per_capita_over_time", lang),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
    )

    return fig


def overview_narrative(df, lang="en"):
    country = df.country_name.iloc[0]

    # Compute segments on-the-fly (filter only on real_expenditure to match pre-computed)
    plot_df = (
        df.dropna(subset=["real_expenditure"])
        .groupby("year")["real_expenditure"].sum()
        .reset_index()
        .sort_values("year")
    )
    extractor = InsightExtractor(plot_df["year"].values, plot_df["real_expenditure"].values)
    trend_narrative = get_segment_narrative(extractor=extractor, metric=t("metric.total_real_expenditure", lang), lang=lang)

    if trend_narrative:
        trend_narrative = trend_narrative[0].lower() + trend_narrative[1:]
        text = t("narrative.after_inflation", lang, trend_narrative=trend_narrative)
    else:
        text = ""
    latest = df[df.year == df.year.max()].iloc[0].to_dict()
    end_year = latest["year"]
    decentral_mean = df.expenditure_decentralization.mean() * 100
    decentral_latest = latest["expenditure_decentralization"] * 100
    decentral_text = t("narrative.decentral_mean", lang, mean=decentral_mean)
    if decentral_latest > 0:
        decentral_text += t("narrative.decentral_latest", lang, year=end_year, pct=decentral_latest)
    text += (
        decentral_text
        if decentral_mean > 0
        else t("narrative.no_regional_data", lang, country=t(f"country.{country}", lang))
    )

    return text



def functional_figure(df, lang="en"):
    categories = sorted(df.func.unique(), reverse=True)

    fig = go.Figure()

    for cat in categories:
        cat_df = df[df.func == cat]
        fig.add_trace(
            go.Bar(
                name=cat,
                x=cat_df.year,
                y=cat_df.percentage,
                marker_color=FUNC_COLORS[cat],
                customdata=cat_df["expenditure_formatted"],
                hovertemplate=(
                    "<b>" + t("hover.year", lang) + "</b>: %{x}<br>"
                    "<b>" + t("hover.expenditure_label", lang) + "</b>: %{customdata} (%{y:.1f}%)"
                ),
            )
        )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        barmode="stack",
        title=t("chart.sector_prioritization", lang),
        plot_bgcolor="white",
        legend=dict(orientation="v", x=1.02, y=1, xanchor="left", yanchor="top"),
    )

    return fig


def functional_narrative(df, lang="en"):
    country = df.country_name.iloc[0]
    categories = df.func.unique().tolist()
    text = t("narrative.func_cofog_intro", lang, country=t(f"country.{country}", lang), count=len(categories))

    def _translate_cofog(name):
        """Translate a raw English COFOG name to the target language."""
        key = COFOG_KEY_MAP.get(name)
        return t(key, lang) if key else name

    if len(categories) < len(COFOG_CATS):
        missing_cats = set(COFOG_CATS) - set(categories)
        translated_missing = [_translate_cofog(c) for c in missing_cats]
        if len(missing_cats) == 1:
            text += t("narrative.func_missing_single", lang, cats=translated_missing[0])
        else:
            text += t("narrative.func_missing_multi", lang, cats=', '.join(translated_missing))

    mean_percentage = df.groupby("func")["percentage"].mean().reset_index()
    n = 3
    top_funcs = mean_percentage.sort_values(by="percentage", ascending=False).head(n)
    text += t("narrative.func_top_n", lang, n=n)
    text += format_func_cats_with_numbers(top_funcs, format_percentage, lang=lang)
    text += "; "

    bottom_funcs = mean_percentage.sort_values(by="percentage", ascending=True).head(n)
    text += t("narrative.func_bottom_n", lang, n=n)
    text += format_func_cats_with_numbers(bottom_funcs, format_percentage, lang=lang)
    text += ". "

    std_percentage = df.groupby("func")["percentage"].std().reset_index()
    m = 2
    stable_funcs = std_percentage.sort_values(by="percentage", ascending=True).head(m)
    text += t("narrative.func_stable", lang)
    text += format_func_cats_with_numbers(stable_funcs, format_std, lang=lang)
    text += "; "

    flux_funcs = std_percentage.sort_values(by="percentage", ascending=False).head(m)
    text += t("narrative.func_fluctuate", lang)
    text += format_func_cats_with_numbers(flux_funcs, format_std, lang=lang)
    text += t("narrative.func_fluctuate_end", lang)

    return text


def format_func_cats_with_numbers(df, format_number_func, lang="en"):
    return format_cats_with_numbers(df, format_func_cat, format_number_func, lang=lang)


def format_cats_with_numbers(df, format_cat_func, format_number_func, lang="en"):
    items = [
        f"{format_cat_func(row, lang)} ({format_number_func(row['percentage'])})"
        for _, row in df.iterrows()
    ]

    # Language-aware conjunction: "and" in English, "et" in French, etc.
    and_word = t("word.and", lang)
    if len(items) == 2:
        return f" {and_word} ".join(items)
    elif len(items) > 2:
        return ", ".join(items[:-1]) + f", {and_word} {items[-1]}"
    elif items:
        return items[0]
    else:
        return ""


def format_percentage(num):
    return f"{num:.1f}%"


def format_std(num):
    return f"std={num:.1f}"


def format_func_cat(row, lang="en"):
    """Return the category label in the target language.

    Falls back to the raw English name if the category isn't in
    COFOG_KEY_MAP (e.g. an unexpected dataset value).
    """
    key = COFOG_KEY_MAP.get(row["func"])
    return t(key, lang) if key else row["func"]


def subnational_spending_narrative(
    df_spending,
    df_poverty,
    currency_code,
    lang="en",
    top_n=3,
    exp_thresh=0.5,
    per_capita_thresh=1000,
):
    total_expenditure = (
        df_spending.groupby("adm1_name")["expenditure"]
        .sum()
        .sort_values(ascending=False)
    )
    top_n_total = total_expenditure.head(top_n)
    total_expenditure_sum = total_expenditure.sum()
    top_n_percentage = top_n_total.sum() / total_expenditure_sum
    per_capita_expenditure = df_spending.groupby("adm1_name")[
        "per_capita_expenditure"
    ].mean()
    per_capita_range = per_capita_expenditure.max() - per_capita_expenditure.min()
    per_capita_median = per_capita_expenditure.median()

    if top_n_percentage > exp_thresh:
        exp_narrative = [
            t("narrative.top_n_concentration", lang,
              n=top_n, regions=', '.join(top_n_total.index),
              pct=f"{top_n_percentage:.1%}"),
        ]
    else:
        exp_narrative = [
            t("narrative.top_n_regions", lang,
              n=top_n, regions=', '.join(top_n_total.index),
              pct=f"{top_n_percentage:.1%}"),
        ]

    exp_narrative.append(html.Em(t("narrative.select_total", lang)))

    if per_capita_range > per_capita_thresh:
        per_capita_narrative = t("narrative.per_capita_wide_variation", lang,
                                  min_val=format_currency(per_capita_expenditure.min(), currency_code),
                                  max_val=format_currency(per_capita_expenditure.max(), currency_code),
                                  median=format_currency(per_capita_median, currency_code))
    else:
        per_capita_narrative = t("narrative.per_capita_even_distribution", lang,
                                  min_val=format_currency(per_capita_expenditure.min(), currency_code),
                                  max_val=format_currency(per_capita_expenditure.max(), currency_code),
                                  median=format_currency(per_capita_median, currency_code))

    corr_narrative = ""
    if not df_poverty.empty:
        poverty_rates = df_poverty.groupby("region_name")["poverty_rate"].mean()
        corr_df = pd.DataFrame({
            "per_capita": per_capita_expenditure,
            "poverty": poverty_rates
        }).dropna()

        if len(corr_df) >= 3:
            corr_narrative = get_correlation_text(
                corr_df,
                x_col={"col_name": "poverty", "display": "poverty rates"},
                y_col={"col_name": "per_capita", "display": "per capita spending"},
                lang=lang,
            )
            corr_narrative = corr_narrative[0].upper() + corr_narrative[1:]

    return [f"{per_capita_narrative} {corr_narrative} "] + exp_narrative



def regional_spending_choropleth(geojson, disputed_geojson, df, zmin, zmax, lat, lon, zoom, theme, lang="en"):
    all_regions = [feature["properties"]["region"] for feature in geojson["features"]]
    regions_without_data = [r for r in all_regions if r not in df.adm1_name.values]
    df_no_data = pd.DataFrame({"region_name": regions_without_data})
    df_no_data["adm1_name"] = None
    if df.empty:
        return empty_plot(t("error.subnat_expenditure_unavailable", lang))
    country_name = df.country_name.iloc[0]
    fig = px.choropleth_mapbox(
        df,
        custom_data=["expenditure_formatted"],
        geojson=geojson,
        color="expenditure",
        locations="adm1_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        mapbox_style="carto-positron",
        zoom=zoom,
        range_color=[zmin, zmax],
        color_continuous_scale=get_map_colorscale(theme),
    )

    no_data_trace = px.choropleth_mapbox(
        df_no_data,
        geojson=geojson,
        color_discrete_sequence=["rgba(211, 211, 211, 0.3)"],
        locations="region_name",
        featureidkey="properties.region",
        zoom=zoom,
    ).data[0]
    no_data_trace.showscale = False
    no_data_trace.showlegend = False
    no_data_trace.hovertemplate = (
        "<b>" + t("hover.region", lang) + ":</b> %{location}<br>"
        "<b>" + t("hover.expenditure_label", lang) + ":</b> " + t("hover.data_not_available", lang) + "<extra></extra>"
    )
    fig.add_trace(no_data_trace)

    fig.update_layout(
        title=t("chart.regional_spending", lang),
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=60, b=80),
        coloraxis_colorbar=dict(
            title="",
            orientation="v",
            thickness=10,
        ),
        legend=dict(orientation="h", x=1.02, y=1, xanchor="left", yanchor="top"),
    )
    fig.data[0].hovertemplate = (
        "<b>" + t("hover.region", lang) + ":</b> %{location}<br>"
        "<b>" + t("hover.expenditure_label", lang) + ":</b> %{z}<extra></extra>"
    )
    fig = add_disputed_overlay(fig, disputed_geojson, zoom)
    return fig


def regional_percapita_spending_choropleth(geojson, disputed_geojson, df, zmin, zmax, lat, lon, zoom, theme, lang="en"):
    all_regions = [feature["properties"]["region"] for feature in geojson["features"]]
    regions_without_data = [r for r in all_regions if r not in df.adm1_name.values]
    df_no_data = pd.DataFrame({"region_name": regions_without_data})
    df_no_data["adm1_name"] = None
    if df.empty:
        return empty_plot(t("error.subnat_population_unavailable", lang))
    country_name = df.country_name.iloc[0]
    df = df[df.adm1_name != "Central Scope"]

    # Dynamically calculate zmin and zmax based on the data range
    zmin = df["per_capita_expenditure"].min() if not df.empty else 0
    zmax = df["per_capita_expenditure"].max() if not df.empty else 1

    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        color="per_capita_expenditure",
        locations="adm1_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        mapbox_style="carto-positron",
        zoom=zoom,
        range_color=[zmin, zmax],
        custom_data=["per_capita_expenditure_formatted"],
        color_continuous_scale=get_map_colorscale(theme),
    )

    no_data_trace = px.choropleth_mapbox(
        df_no_data,
        geojson=geojson,
        color_discrete_sequence=["rgba(211, 211, 211, 0.3)"],
        locations="region_name",
        featureidkey="properties.region",
        zoom=zoom,
    ).data[0]
    no_data_trace.showscale = False
    no_data_trace.showlegend = False
    no_data_trace.hovertemplate = (
        "<b>" + t("hover.region", lang) + ":</b> %{location}<br>"
        "<b>Per capita expenditure:</b> " + t("hover.data_not_available", lang) + "<extra></extra>"
    )
    fig.add_trace(no_data_trace)

    fig.update_layout(
        title=t("chart.regional_per_capita", lang),
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=60, b=80),
        coloraxis_colorbar=dict(
            title="",
            orientation="v",
            thickness=10,
        ),
    )
    fig.data[0].hovertemplate = (
        "<b>" + t("hover.region", lang) + ":</b> %{location}<br>"
        + "<b>Per capita expenditure:</b> %{customdata[0]}<extra></extra>"
    )
    fig = add_disputed_overlay(fig, disputed_geojson, zoom)

    return fig


INCOME_LEVEL_THRESHOLD = {
    "LIC": ("$3.00", "Low Income"),
    "LMC": ("$4.20", "Lower Middle Income"),
    "UMC": ("$8.30", "Upper Middle Income"),
    "HIC": ("$8.30", "High Income"),
}

def subnational_poverty_choropleth(geojson, disputed_geojson, df, zmin, zmax, lat, lon, zoom, income_level, theme, lang="en"):
    if df[df.region_name != "National"].empty:
        return empty_plot(t("error.subnat_poverty_unavailable", lang))
    # TODO align accents across all datasets
    df = df.copy()
    df["region_name"] = df.region_name.map(lambda x: remove_accents(x))
    poverty_col = "poverty_rate"
    df[poverty_col] = df[poverty_col] * 100
    zmin = zmin * 100 if zmin is not None else None
    zmax = zmax * 100 if zmax is not None else None
    country_name = df.country_name.iloc[0]
    year = df.year.iloc[0]
    all_regions = [feature["properties"]["region"] for feature in geojson["features"]]
    regions_without_data = [r for r in all_regions if r not in df.region_name.values]
    df_no_data = pd.DataFrame({"region_name": regions_without_data})
    df_no_data[poverty_col] = None
    fig = px.choropleth_mapbox(
        df,
        geojson=geojson,
        color=poverty_col,
        locations="region_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        zoom=zoom,
        range_color=[zmin, zmax],
        mapbox_style="carto-positron",
        hover_data={"region_name": True, poverty_col: ":.2f"},
        color_continuous_scale=get_map_colorscale(theme),
    )

    no_data_trace = px.choropleth_mapbox(
        df_no_data,
        geojson=geojson,
        color_discrete_sequence=["rgba(211, 211, 211, 0.3)"],
        locations="region_name",
        featureidkey="properties.region",
        zoom=zoom,
        hover_data={"region_name": True},
    ).data[0]
    no_data_trace.showscale = False
    no_data_trace.showlegend = False
    no_data_trace.hovertemplate = (
        "<b>" + t("hover.region", lang) + ":</b> %{location}<br>"
        "<b>Poverty rate:</b> " + t("hover.data_not_available", lang) + "<extra></extra>"
    )
    fig.add_trace(no_data_trace)

    fig.update_layout(
        title=t("chart.poverty_map", lang),
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=60, b=80),
        coloraxis_colorbar=dict(
            title="",
            orientation="v",
            thickness=10,
        ),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.13,
                xanchor="left",
                text=t("annotation.displaying_data_from", lang, year=year) + " " + _get_poverty_source_text(income_level, lang),
                showarrow=False,
                font=dict(size=10),
            ),
        ],
    )
    fig.data[0].hovertemplate = (
        "<b>" + t("hover.region", lang) + ":</b> %{location}<br>"
        + "<b>Poverty rate:</b> %{z:.2f}%<extra></extra>"
    )
    fig = add_disputed_overlay(fig, disputed_geojson, zoom)

    return fig


def _get_poverty_source_text(income_level, lang="en"):
    if income_level and income_level in INCOME_LEVEL_THRESHOLD:
        threshold, level_name = INCOME_LEVEL_THRESHOLD[income_level]
        return t("annotation.poverty_threshold", lang, threshold=threshold, level_name=level_name)
    return t("annotation.poverty_threshold_default", lang)


@callback(
    Output("regional-expenditure-heading", "children"),
    Input("country-select", "value"),
    Input("stored-language", "data"),
)
def update_heading(country, lang):
    lang = lang or "en"
    if not country:
        return t("heading.regional_expenditure", lang)
    country_display = t(f"country.{country}", lang)
    return t(
        "heading.country_regional_expenditure", lang,
        country=country_display, country_gen=genitive(lang, country_display),
    )


@callback(
    Output("overview-total", "figure"),
    Output("overview-per-capita", "figure"),
    Output("overview-narrative", "children"),
    Input("stored-data", "data"),
    Input('stored-basic-country-data', 'data'),
    Input("country-select", "value"),
    Input("stored-language", "data"),
)
def render_overview_total_figure(data, basic_country_data, country, lang):
    lang = lang or "en"
    if not data or not basic_country_data:
        return dash.no_update, dash.no_update, dash.no_update
    all_countries = pd.DataFrame(data["expenditure_w_poverty_by_country_year"])
    df = filter_country_sort_year(all_countries, country)

    # Extract currency_name once at callback level
    basic_info = pd.DataFrame(basic_country_data['basic_country_info']).T.loc[country]
    currency_name = basic_info['currency_name']
    currency_code = basic_info['currency_code']
    return total_figure(df, currency_name, currency_code, lang=lang), per_capita_figure(df, currency_name, currency_code, lang=lang), overview_narrative(df, lang=lang)


@callback(
    Output("functional-breakdown", "figure"),
    Output("functional-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("country-select", "value"),
    Input('stored-basic-country-data', 'data'),
    Input("stored-language", "data"),
)
def render_overview_func_figure(data, country, basic_country_data, lang):
    lang = lang or "en"
    if not data or not basic_country_data:
        return dash.no_update, dash.no_update
    all_countries = pd.DataFrame(data["expenditure_by_country_func_year"])
    func_df = filter_country_sort_year(all_countries, country)
    total_per_year = func_df.groupby("year")["expenditure"].sum().reset_index()
    func_df = func_df.merge(total_per_year, on="year", suffixes=("", "_total"))
    func_df["percentage"] = (
        func_df["expenditure"] / func_df["expenditure_total"]
    ) * 100
    currency_code = basic_country_data["basic_country_info"][country]["currency_code"]
    func_df["expenditure_formatted"] = func_df["expenditure"].apply(
        lambda x: format_currency(x, currency_code)
    )

    return functional_figure(func_df, lang=lang), functional_narrative(func_df, lang=lang)


@callback(
    Output("economic-breakdown", "figure"),
    Output("economic-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("country-select", "value"),
    Input('stored-basic-country-data', 'data'),
    Input("stored-language", "data"),
)
def render_overview_econ_figure(data, country, basic_country_data, lang):
    lang = lang or "en"
    if not data or not basic_country_data:
        return dash.no_update, dash.no_update
    all_countries = pd.DataFrame(data["expenditure_by_country_econ_year"])
    econ_df = filter_country_sort_year(all_countries, country)
    total_per_year = econ_df.groupby("year")["expenditure"].sum().reset_index()
    econ_df = econ_df.merge(total_per_year, on="year", suffixes=("", "_total"))
    econ_df["percentage"] = (
        econ_df["expenditure"] / econ_df["expenditure_total"]
    ) * 100

    currency_code = basic_country_data["basic_country_info"][country]["currency_code"]

    return economic_figure(econ_df, currency_code, lang=lang), economic_narrative(econ_df, lang=lang)


ECON_CAT_MAP = {
    "Capital expenditures": "Capital expenditures",
    "Goods and services": "Goods and services",
    "Social benefits": "Social benefits",
    "Subsidies": "Subsidies",
    "Wage bill": "Employees compensation",
    "Interest on debt": "Interest on debt",
    "Other grants and transfers": "Grants and transfers",
    "Other expenses": "Other expenses",
}

# Maps raw English econ data values (the `econ` column in the dataset) to
# the translation key used in en.py/fr.py. Mirrors COFOG_KEY_MAP in spirit.
ECON_KEY_MAP = {
    "Capital expenditures":         "econ.capital_expenditures",
    "Goods and services":           "econ.goods_services",
    "Social benefits":              "econ.social_benefits",
    "Subsidies":                    "econ.subsidies",
    "Wage bill":                    "econ.employees_compensation",
    "Interest on debt":             "econ.interest_debt",
    "Other grants and transfers":   "econ.grants_transfers",
    "Other expenses":               "econ.other_expenses",
}
ECON_PALETTE = QUALITATIVE_ALT
ECON_COLORS = {
    cat: ECON_PALETTE[i % len(ECON_PALETTE)]
    for i, cat in enumerate(ECON_CAT_MAP.keys())
}


def economic_figure(df, currency_code, lang="en"):
    categories = sorted(df.econ.unique(), reverse=True)

    fig = go.Figure()

    for cat in categories:
        cat_df = df[df.econ == cat]
        cat_df_with_formatted = cat_df.copy()
        cat_df_with_formatted['expenditure_formatted'] = cat_df_with_formatted['expenditure'].apply(
            lambda x: format_currency(x, currency_code)
        )
        fig.add_trace(
            go.Bar(
                name=ECON_CAT_MAP[cat],
                x=cat_df.year,
                y=cat_df.percentage,
                marker_color=ECON_COLORS[cat],
                customdata=np.column_stack([cat_df_with_formatted['expenditure_formatted']]),
                hovertemplate=(
                    "<b>" + t("hover.year", lang) + "</b>: %{x}<br>"
                    "<b>" + t("hover.expenditure_label", lang) + "</b>: %{customdata} (%{y:.1f}%)"
                ),
            )
        )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        barmode="stack",
        title=t("chart.econ_category_spending", lang),
        plot_bgcolor="white",
        legend=dict(orientation="v", x=1.02, y=1, xanchor="left", yanchor="top"),
    )

    return fig


def economic_narrative(df, lang="en"):
    country = df.country_name.iloc[0]
    categories = df.econ.unique().tolist()
    text = t("narrative.econ_intro", lang, country=t(f"country.{country}", lang), count=len(categories))

    def _translate_econ(raw):
        """Translate a raw dataset econ value to the target language."""
        key = ECON_KEY_MAP.get(raw)
        return t(key, lang) if key else ECON_CAT_MAP.get(raw, raw)

    if len(categories) < len(ECON_CAT_MAP):
        missing_cats = set(ECON_CAT_MAP.keys()) - set(categories)
        translated_missing = [_translate_econ(c) for c in missing_cats]
        if len(translated_missing) == 1:
            text += t("narrative.econ_missing_single", lang, cats=translated_missing[0])
        else:
            text += t("narrative.econ_missing_multi", lang, cats=', '.join(translated_missing))

    mean_percentage = df.groupby("econ")["percentage"].mean().reset_index()
    n = 3
    top_econs = mean_percentage.sort_values(by="percentage", ascending=False).head(n)
    text += t("narrative.econ_top_n", lang, n=n)
    text += format_econ_cats_with_numbers(top_econs, format_percentage, lang=lang)
    text += "; "

    bottom_econs = mean_percentage.sort_values(by="percentage", ascending=True).head(n)
    text += t("narrative.econ_bottom_n", lang, n=n)
    text += format_econ_cats_with_numbers(bottom_econs, format_percentage, lang=lang)
    text += ". "

    std_percentage = df.groupby("econ")["percentage"].std().reset_index()
    m = 2
    stable_econs = std_percentage.sort_values(by="percentage", ascending=True).head(m)
    text += t("narrative.econ_stable", lang)
    text += format_econ_cats_with_numbers(stable_econs, format_std, lang=lang)
    text += "; "

    flux_econs = std_percentage.sort_values(by="percentage", ascending=False).head(m)
    text += t("narrative.econ_fluctuate", lang)
    text += format_econ_cats_with_numbers(flux_econs, format_std, lang=lang)
    text += t("narrative.econ_fluctuate_end", lang)

    return text


def format_econ_cats_with_numbers(df, format_number_func, lang="en"):
    return format_cats_with_numbers(df, format_econ_cat, format_number_func, lang=lang)


def format_econ_cat(row, lang="en"):
    """Return the economic category label in the target language.

    Falls back to the ECON_CAT_MAP display label if the category isn't in
    ECON_KEY_MAP.
    """
    key = ECON_KEY_MAP.get(row["econ"])
    if key:
        return t(key, lang)
    return ECON_CAT_MAP.get(row["econ"], row["econ"])


@callback(
    Output("year-slider-container", "style"),
    Output("year-slider", "marks"),
    Output("year-slider", "value"),
    Output("year-slider", "min"),
    Output("year-slider", "max"),
    Output("year-slider", "tooltip"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
)
def update_year_range(data, country):
    try:
        data = data["basic_country_info"]
        expenditure_years = data[country].get("expenditure_years", [])
        poverty_years = data[country].get("poverty_years", [])

        slider_configs = get_slider_config(expenditure_years, poverty_years)
        return slider_configs
    except Exception as e:
        return {"display": "block"}, {}, 0, 0, 0, {}


@callback(
    Output("subnational-spending", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("expenditure-plot-radio", "value"),
    Input("year-slider", "value"),
    Input("stored-data-subnat-boundaries", "data"),
    Input("stored-language", "data"),
    State("theme-store", "data"),
)
def render_subnational_spending_figures(data, country_data, country, plot_type, year, subnat_boundaries, lang, theme):
    lang = lang or "en"
    if year is None or not data or not country_data or not country:
        return empty_plot(t("error.data_not_available", lang))

    geojson = subnat_boundaries[country]
    disputed_geojson = filter_geojson_by_country(data["disputed_boundaries"], country)
    lat, lon = [
        country_data["basic_country_info"][country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = country_data["basic_country_info"][country]["zoom"]

    filtered_geojson = filter_geojson_by_country(geojson, country)
    df = pd.DataFrame(data["expenditure_by_country_geo1_year"])
    df = filter_country_sort_year(df, country)
    df = df[df.adm1_name != "Central Scope"]
    currency_code = country_data["basic_country_info"][country]["currency_code"]
    add_currency_column(df, 'expenditure', currency_code)
    add_currency_column(df, 'per_capita_expenditure', currency_code)

    if df.empty or year not in df.year.unique():
        return empty_plot(t("error.no_expenditure_data_year", lang))

    df_for_year = df[df.year == year]
    legend_percapita_min, legend_percapita_max = (
        df_for_year.per_capita_expenditure.min(),
        df_for_year.per_capita_expenditure.max(),
    )
    legend_expenditure_min, legend_expenditure_max = (
        df_for_year.expenditure.min(),
        df_for_year.expenditure.max(),
    )

    if plot_type == "percapita":
        return regional_percapita_spending_choropleth(
            filtered_geojson,
            disputed_geojson,
            df_for_year,
            legend_percapita_min,
            legend_percapita_max,
            lat,
            lon,
            zoom,
            theme=theme,
            lang=lang,
        )
    else:
        return regional_spending_choropleth(
            filtered_geojson,
            disputed_geojson,
            df_for_year,
            legend_expenditure_min,
            legend_expenditure_max,
            lat,
            lon,
            zoom,
            theme=theme,
            lang=lang,
        )


@callback(
    Output("subnational-poverty", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider", "value"),
    Input("stored-data-subnat-boundaries", "data"),
    Input("stored-language", "data"),
    State("theme-store", "data"),
)
def render_subnational_poverty_figure(subnational_data, country_data, country, year, subnat_boundaries, lang, theme):
    lang = lang or "en"
    if year is None or not subnational_data or not country_data or not country:
        return empty_plot(t("error.data_not_available", lang))

    geojson = subnat_boundaries[country]
    disputed_geojson = filter_geojson_by_country(
        subnational_data["disputed_boundaries"], country
    )
    filtered_geojson = filter_geojson_by_country(geojson, country)
    df = pd.DataFrame(subnational_data["subnational_poverty_rate"])
    df = filter_country_sort_year(df, country)

    legend_min, legend_max = country_data["basic_country_info"][country].get(
        "poverty_bounds", (None, None)
    )
    lat, lon = [
        country_data["basic_country_info"][country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = country_data["basic_country_info"][country]["zoom"]

    available_years = country_data["basic_country_info"][country].get(
        "poverty_years", []
    )
    relevant_years = [x for x in available_years if x <= year]

    if not relevant_years or df.empty:
        return empty_plot(t("error.poverty_unavailable", lang))

    income_level = country_data["basic_country_info"][country].get("income_level")
    return subnational_poverty_choropleth(
        filtered_geojson,
        disputed_geojson,
        df[df.year == relevant_years[-1]],
        legend_min,
        legend_max,
        lat,
        lon,
        zoom,
        income_level,
        theme=theme,
        lang=lang,
    )


@callback(
    Output("subnational-spending-narrative", "children"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider", "value"),
    Input("stored-language", "data"),
)
def render_subnational_spending_narrative(
    subnational_data, country_data, country, year, lang
):
    lang = lang or "en"
    if year is None or not subnational_data or not country_data or not country:
        return t("error.data_not_available", lang)

    df_poverty = pd.DataFrame(subnational_data["subnational_poverty_rate"])
    df_poverty = filter_country_sort_year(df_poverty, country)

    available_years = country_data["basic_country_info"][country].get(
        "poverty_years", []
    )
    currency_code = country_data["basic_country_info"][country]["currency_code"]
    relevant_years = [x for x in available_years if x <= year]

    if not relevant_years or df_poverty.empty:
        df_poverty = pd.DataFrame()

    df_spending = pd.DataFrame(subnational_data["expenditure_by_country_geo1_year"])
    df_spending = filter_country_sort_year(df_spending, country)
    df_spending = df_spending[
        (df_spending.adm1_name != "Central Scope") & (df_spending.year == year)
    ]

    if df_spending.empty:
        return t("error.no_spending_data", lang)

    return subnational_spending_narrative(df_spending, df_poverty, currency_code, lang=lang)


@callback(
    Output("pefa-narrative", "children"),
    Output("pefa-overall", "figure"),
    Output("pefa-by-pillar", "figure"),
    Input("stored-data", "data"),
    Input("stored-data-pefa", "data"),
    Input("country-select", "value"),
    Input("stored-language", "data"),
)
def render_pefa_overall(data, pefa_data, country, lang):
    lang = lang or "en"
    if not pefa_data or not data:
        return dash.no_update, dash.no_update, dash.no_update

    pefa_df = pd.DataFrame(pefa_data["pefa"])
    country_pefa_df = filter_country_sort_year(pefa_df, country)

    all_countries_pov = pd.DataFrame(data["expenditure_w_poverty_by_country_year"])
    country_pov_df = filter_country_sort_year(all_countries_pov, country)

    return (
        pefa.pefa_narrative(country_pefa_df, lang=lang),
        pefa.pefa_overall_figure(country_pefa_df, country_pov_df, lang=lang),
        pefa.pefa_pillar_heatmap(country_pefa_df, lang=lang),
    )


@callback(
    Output("func-growth", "figure"),
    Output("func-growth-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("country-select", "value"),
    Input("budget-increment-radio", "value"),
    Input("stored-language", "data"),
)
def render_budget_func_changes(data, country, exp_type, lang):
    lang = lang or "en"
    return budget_increment_analysis.render_fig_and_narrative(data, country, exp_type, lang=lang)
