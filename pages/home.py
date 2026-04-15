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
from constants import COFOG_CATS, FUNC_COLORS, MAP_DISCLAIMER
from viz_theme import QUALITATIVE_ALT, get_map_colorscale, CENTRAL_COLOR, REGIONAL_COLOR
from queries import QueryService
import server_store


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
                            children=[
                                dbc.Tab(label="Over Time", tab_id="overview-tab-time"),
                                dbc.Tab(
                                    label="Across Space", tab_id="overview-tab-space"
                                ),
                            ],
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
    Output("stored-data-pefa", "data"),
    Input("stored-data-pefa", "data"),
    Input("stored-data", "data"),
)
def fetch_pefa_data_once(pefa_data, shared_data):
    if pefa_data is None and shared_data:
        server_store.get("pefa")
        return {"ready": True}
    return dash.no_update

@callback(
    Output("overview-content", "children"),
    Input("overview-tabs", "active_tab"),
)
def render_overview_content(tab):
    if tab == "overview-tab-time":
        return html.Div(
            [
                dbc.Row(
                    dbc.Col(
                        html.H3(children="Total Expenditure")
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.P(
                            id="overview-narrative",
                            children="loading...",
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
                        html.H3(children="Spending by Functional Categories")
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
                                children="loading...",
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
                                children="loading...",
                            ),
                            html.P(
                                id="func-growth-instruction",
                                children=html.Small(html.Em("By default, only Overall Budget, Health, Education, and General Public Services are shown in the chart. Click on the legend to view the year-on-year budget growth rate for other functional categories.")),
                            )
                        ], xs=12, lg=4),
                        dbc.Col([
                            html.Div([
                                dbc.RadioItems(
                                    id="budget-increment-radio",
                                    options=[
                                        {
                                            "label": "Budget",
                                            "value": "domestic_funded_budget",
                                        },
                                        {
                                            "label": "Inflation-adjusted Budget",
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
                        html.H3(children="Spending by Economic Categories")
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
                                children="loading...",
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
                        html.H3(children="Quality of Budget Institutions")
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        html.P(
                            id="pefa-narrative",
                            children="loading...",
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
                            children="Regional Expenditure",
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
                                            "label": "  Per capita expenditure",
                                            "value": "percapita",
                                        },
                                        {
                                            "label": "  Total expenditure",
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
                                disclaimer_tooltip("warning-sign", MAP_DISCLAIMER),
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
                                children="loading ...",
                            ),
                        ]
                    )
                ),
                html.Div(style={"height": "20px"}),
            ]
        )


def total_figure(df, currency_name, currency_code):
    fig = go.Figure()
    add_currency_column(df, 'real_expenditure', currency_code)
    df['central_expenditure_formatted'] = (df['expenditure'] - df['decentralized_expenditure']).apply(lambda x: format_currency(x, currency_code))
    add_currency_column(df, 'decentralized_expenditure', currency_code)
    fig.add_trace(
        go.Scatter(
            name="Inflation Adjusted",
            x=df.year,
            y=df.real_expenditure,
            mode="lines+markers",
            marker_color="darkblue",
            customdata=np.column_stack([df['real_expenditure_formatted']]),
            hovertemplate="Inflation Adjusted Expenditure: %{customdata[0]}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Central",
            x=df.year,
            y=df.expenditure - df.decentralized_expenditure,
            marker_color=CENTRAL_COLOR,
            customdata=np.column_stack([df['central_expenditure_formatted']]),
            hovertemplate="Central Expenditure: %{customdata[0]}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Regional",
            x=df.year,
            y=df.decentralized_expenditure,
            marker_color=REGIONAL_COLOR,
            customdata=np.column_stack([df['decentralized_expenditure_formatted']]),
            hovertemplate="Regional Expenditure: %{customdata[0]}<extra></extra>",
        )
    )

    format_currency_yaxis(fig, currency_name, "Total Expenditure")
    fig.update_layout(
        barmode="stack",
        title="How has total expenditure changed over time?",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
        hovermode="x unified",
    )

    return fig


def per_capita_figure(df, currency_name, currency_code):
    add_currency_column(df, 'per_capita_expenditure', currency_code)
    add_currency_column(df, 'per_capita_real_expenditure', currency_code)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # TODO: add a note to Details modal, explaining poverty rate threshold used is country income-level dependent
    fig.add_trace(
        go.Scatter(
            name="Poverty Rate",
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
            name="Inflation Adjusted",
            x=df.year,
            y=df.per_capita_real_expenditure,
            mode="lines+markers",
            marker_color="darkblue",
            customdata=np.column_stack([df['per_capita_real_expenditure_formatted']]),
            hovertemplate="Inflation Adjusted Per Capita Public Spending: %{customdata[0]}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            name="Per Capita",
            x=df.year,
            y=df.per_capita_expenditure,
            marker_color="#686dc3",
            customdata=np.column_stack([df['per_capita_expenditure_formatted']]),
            hovertemplate="Per Capita Public Spending: %{customdata[0]}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(title_text=f"Per Capita Expenditure ({currency_name})", secondary_y=False, fixedrange=True)
    fig.update_yaxes(
        title_text="Poverty Rate (%)",
        secondary_y=True,
        range=[-1, 100],
    )
    fig.update_layout(
        hovermode="x unified",
        barmode="stack",
        title="How has per capita expenditure changed over time?",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
    )

    return fig


def overview_narrative(df):
    country = df.country_name.iloc[0]

    # Compute segments on-the-fly (filter only on real_expenditure to match pre-computed)
    plot_df = (
        df.dropna(subset=["real_expenditure"])
        .groupby("year")["real_expenditure"].sum()
        .reset_index()
        .sort_values("year")
    )
    extractor = InsightExtractor(plot_df["year"].values, plot_df["real_expenditure"].values)
    trend_narrative = get_segment_narrative(extractor=extractor, metric="total real expenditure")

    if trend_narrative:
        trend_narrative = trend_narrative[0].lower() + trend_narrative[1:]
        text = f"After accounting for inflation, {trend_narrative} "
    else:
        text = ""
    latest = df[df.year == df.year.max()].iloc[0].to_dict()
    end_year = latest["year"]
    decentral_mean = df.expenditure_decentralization.mean() * 100
    decentral_latest = latest["expenditure_decentralization"] * 100
    decentral_text = f"On average, {decentral_mean:.1f}% of total public spending is executed by local/regional government. "
    if decentral_latest > 0:
        decentral_text += f"In {end_year}, which is the latest year with data available, expenditure decentralization is {decentral_latest:.1f}%. "
    text += (
        decentral_text
        if decentral_mean > 0
        else f"BOOST does not have any local/regional spending data for {country}. "
    )

    return text



def functional_figure(df):
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
                    "<b>Year</b>: %{x}<br>"
                    "<b>Expenditure</b>: %{customdata} (%{y:.1f}%)"
                ),
            )
        )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        barmode="stack",
        title="How has sector prioritization changed over time?",
        plot_bgcolor="white",
        legend=dict(orientation="v", x=1.02, y=1, xanchor="left", yanchor="top"),
    )

    return fig


def functional_narrative(df):
    country = df.country_name.iloc[0]
    categories = df.func.unique().tolist()
    text = f"For {country}, BOOST provides functional spending data on {len(categories)} categories, based on Classification of the Functions of Government (COFOG). "

    if len(categories) < len(COFOG_CATS):
        missing_cats = set(COFOG_CATS) - set(categories)
        if len(missing_cats) == 1:
            text += f"The cartegory we do not have data on is {list(missing_cats)[0]}. "
        else:
            text += f"The cartegories we do not have data on include {', '.join(missing_cats)}. "

    mean_percentage = df.groupby("func")["percentage"].mean().reset_index()
    n = 3
    top_funcs = mean_percentage.sort_values(by="percentage", ascending=False).head(n)
    text += f"On average, the top {n} spending functional categories are "
    text += format_func_cats_with_numbers(top_funcs, format_percentage)
    text += "; "

    bottom_funcs = mean_percentage.sort_values(by="percentage", ascending=True).head(n)
    text += f"while the bottom {n} spenders are "
    text += format_func_cats_with_numbers(bottom_funcs, format_percentage)
    text += ". "

    std_percentage = df.groupby("func")["percentage"].std().reset_index()
    m = 2
    stable_funcs = std_percentage.sort_values(by="percentage", ascending=True).head(m)
    text += f"Relatively, public expenditure remain the most stable in "
    text += format_func_cats_with_numbers(stable_funcs, format_std)
    text += "; "

    flux_funcs = std_percentage.sort_values(by="percentage", ascending=False).head(m)
    text += f"while spending in "
    text += format_func_cats_with_numbers(flux_funcs, format_std)
    text += f" fluctuate the most over time. "

    return text


def format_func_cats_with_numbers(df, format_number_func):
    return format_cats_with_numbers(df, format_func_cat, format_number_func)


def format_cats_with_numbers(df, format_cat_func, format_number_func):
    items = [
        f"{format_cat_func(row)} ({format_number_func(row['percentage'])})"
        for _, row in df.iterrows()
    ]

    if len(items) == 2:
        return " and ".join(items)
    elif len(items) > 2:
        return ", ".join(items[:-1]) + f", and {items[-1]}"
    elif items:
        return items[0]
    else:
        return ""


def format_percentage(num):
    return f"{num:.1f}%"


def format_std(num):
    return f"std={num:.1f}"


def format_func_cat(row):
    return row["func"]


def subnational_spending_narrative(
    df_spending,
    df_poverty,
    currency_code,
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
            f"The top {top_n} regions—{', '.join(top_n_total.index)}—account for {top_n_percentage:.1%} of the total government expenditure, indicating a significant concentration in these areas. ",
        ]
    else:
        exp_narrative = [f"The top {top_n} regions—{', '.join(top_n_total.index)}—account for {top_n_percentage:.1%} of the total government expenditure."]

    exp_narrative.append(html.Em("(Select the Total expenditure option above to see the breakdown by total amount)."))

    if per_capita_range > per_capita_thresh:
        per_capita_narrative = f"Per capita spending varies widely across regions, ranging from {format_currency(per_capita_expenditure.min(), currency_code)} \
            to {format_currency(per_capita_expenditure.max(), currency_code)}, with a median of {format_currency(per_capita_median, currency_code)}. This indicates substantial variation in resource allocation per person."
    else:
        per_capita_narrative = f"Per capita spending ranges from {format_currency(per_capita_expenditure.min(), currency_code)} to {format_currency(per_capita_expenditure.max(), currency_code)}, \
            with a median of {format_currency(per_capita_median, currency_code)}. The distribution is relatively even across regions."

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
            )
            corr_narrative = corr_narrative[0].upper() + corr_narrative[1:]

    return [f"{per_capita_narrative} {corr_narrative} "] + exp_narrative



def regional_spending_choropleth(geojson, disputed_geojson, df, zmin, zmax, lat, lon, zoom, theme):
    all_regions = [feature["properties"]["region"] for feature in geojson["features"]]
    regions_without_data = [r for r in all_regions if r not in df.adm1_name.values]
    df_no_data = pd.DataFrame({"region_name": regions_without_data})
    df_no_data["adm1_name"] = None
    if df.empty:
        return empty_plot("Sub-national expenditure data not available")
    country_name = df.country_name.iloc[0]
    fig = px.choropleth_mapbox(
        df,
        custom_data=["expenditure_formatted"],
        geojson=geojson,
        color="expenditure",
        locations="adm1_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        mapbox_style="white-bg",
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
    no_data_trace.hovertemplate = "<b>Region:</b> %{location}<br><b>Expenditure:</b> Data not available<extra></extra>"
    fig.add_trace(no_data_trace)
    
    fig.update_layout(
        title="How much was spent in each region?",
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=60, b=80),
        coloraxis_colorbar=dict(
            title="",
            orientation="v",
            thickness=10,
        ),
        legend=dict(orientation="h", x=1.02, y=1, xanchor="left", yanchor="top"),
    )
    fig.data[0].hovertemplate = "<b>Region:</b> %{location}<br><b>Expenditure:</b> %{z}<extra></extra>"
    fig = add_disputed_overlay(fig, disputed_geojson, zoom)
    return fig


def regional_percapita_spending_choropleth(geojson, disputed_geojson, df, zmin, zmax, lat, lon, zoom, theme):
    all_regions = [feature["properties"]["region"] for feature in geojson["features"]]
    regions_without_data = [r for r in all_regions if r not in df.adm1_name.values]
    df_no_data = pd.DataFrame({"region_name": regions_without_data})
    df_no_data["adm1_name"] = None
    if df.empty:
        return empty_plot("Sub-national population data not available ")
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
        mapbox_style="white-bg",
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
    no_data_trace.hovertemplate = "<b>Region:</b> %{location}<br><b>Per capita expenditure:</b> Data not available<extra></extra>"
    fig.add_trace(no_data_trace)

    fig.update_layout(
        title="How much was spent per person in each region?",
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=60, b=80),
        coloraxis_colorbar=dict(
            title="",
            orientation="v",
            thickness=10,
        ),
    )
    fig.data[0].hovertemplate = (
        "<b>Region:</b> %{location}<br>"
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

def subnational_poverty_choropleth(geojson, disputed_geojson, df, zmin, zmax, lat, lon, zoom, income_level, theme):
    if df[df.region_name != "National"].empty:
        return empty_plot("Sub-national poverty data not available")
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
        mapbox_style="white-bg",
        hover_data={"region_name": True, poverty_col: ":.2f"},
        color_continuous_scale=get_map_colorscale(theme),
    )
    # TODO: add a note to Details modal, explaining poverty rate threshold used is country income-level dependent

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
    no_data_trace.hovertemplate = "<b>Region:</b> %{location}<br><b>Poverty rate:</b> Data not available<extra></extra>"
    fig.add_trace(no_data_trace)

    fig.update_layout(
        title="What percent of the population is living in poverty?",
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
                text=f"Displaying data from {year}. {_get_poverty_source_text(income_level)}",
                showarrow=False,
                font=dict(size=10),
            ),
        ],
    )
    fig.data[0].hovertemplate = (
        "<b>Region:</b> %{location}<br>"
        + "<b>Poverty rate:</b> %{z:.2f}%<extra></extra>"
    )
    fig = add_disputed_overlay(fig, disputed_geojson, zoom)

    return fig


def _get_poverty_source_text(income_level):
    if income_level and income_level in INCOME_LEVEL_THRESHOLD:
        threshold, level_name = INCOME_LEVEL_THRESHOLD[income_level]
        return f"Poverty rate ({threshold} threshold for {level_name} country)."
    return "Poverty rate ($3.00 threshold)."


@callback(
    Output("regional-expenditure-heading", "children"),
    Input("country-select", "value"),
)
def update_heading(country):
    if not country:
        return "Regional Expenditure"
    return f"{country} Regional Expenditure"


@callback(
    Output("overview-total", "figure"),
    Output("overview-per-capita", "figure"),
    Output("overview-narrative", "children"),
    Input("stored-data", "data"),
    Input('stored-basic-country-data', 'data'),
    Input("country-select", "value"),
)
def render_overview_total_figure(data, basic_country_data, country):
    if not data or not basic_country_data or not country:
        return dash.no_update, dash.no_update, dash.no_update
    all_countries = server_store.get("expenditure_w_poverty")
    df = filter_country_sort_year(all_countries, country)

    # Extract currency_name once at callback level
    basic_info = server_store.get("basic_country_info")[country]
    currency_name = basic_info['currency_name']
    currency_code = basic_info['currency_code']
    return total_figure(df, currency_name, currency_code), per_capita_figure(df, currency_name, currency_code), overview_narrative(df)


@callback(
    Output("functional-breakdown", "figure"),
    Output("functional-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("country-select", "value"),
    Input('stored-basic-country-data', 'data')
)
def render_overview_func_figure(data, country, basic_country_data):
    if not data or not basic_country_data or not country:
        return dash.no_update, dash.no_update
    all_countries = server_store.get("func_by_country_year")
    func_df = filter_country_sort_year(all_countries, country)
    total_per_year = func_df.groupby("year")["expenditure"].sum().reset_index()
    func_df = func_df.merge(total_per_year, on="year", suffixes=("", "_total"))
    func_df["percentage"] = (
        func_df["expenditure"] / func_df["expenditure_total"]
    ) * 100
    currency_code = server_store.get("basic_country_info")[country]["currency_code"]
    func_df["expenditure_formatted"] = func_df["expenditure"].apply(
        lambda x: format_currency(x, currency_code)
    )

    return functional_figure(func_df), functional_narrative(func_df)


@callback(
    Output("economic-breakdown", "figure"),
    Output("economic-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("country-select", "value"),
    Input('stored-basic-country-data', 'data')
)
def render_overview_econ_figure(data, country, basic_country_data):
    if not data or not basic_country_data or not country:
        return dash.no_update, dash.no_update
    all_countries = server_store.get("econ_by_country_year")
    econ_df = filter_country_sort_year(all_countries, country)
    total_per_year = econ_df.groupby("year")["expenditure"].sum().reset_index()
    econ_df = econ_df.merge(total_per_year, on="year", suffixes=("", "_total"))
    econ_df["percentage"] = (
        econ_df["expenditure"] / econ_df["expenditure_total"]
    ) * 100

    currency_code = server_store.get("basic_country_info")[country]["currency_code"]

    return economic_figure(econ_df, currency_code), economic_narrative(econ_df)


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
ECON_PALETTE = QUALITATIVE_ALT
ECON_COLORS = {
    cat: ECON_PALETTE[i % len(ECON_PALETTE)]
    for i, cat in enumerate(ECON_CAT_MAP.keys())
}


def economic_figure(df, currency_code):
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
                    "<b>Year</b>: %{x}<br>"
                    "<b>Expenditure</b>: %{customdata} (%{y:.1f}%)"
                ),
            )
        )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(
        barmode="stack",
        title="How much was spent on each economic category?",
        plot_bgcolor="white",
        legend=dict(orientation="v", x=1.02, y=1, xanchor="left", yanchor="top"),
    )

    return fig


def economic_narrative(df):
    country = df.country_name.iloc[0]
    categories = df.econ.unique().tolist()
    text = f"For {country}, BOOST provides spending data on {len(categories)} economic categories, generally based on Economic Classification of Expense outlined in the Government Finance Statistics (GFS) framework. "

    if len(categories) < len(ECON_CAT_MAP):
        missing_cats = set(ECON_CAT_MAP.keys()) - set(categories)
        missing_cats = list(ECON_CAT_MAP[c] for c in missing_cats)
        if len(missing_cats) == 1:
            text += f"The cartegory we do not have data on is {missing_cats[0]}. "
        else:
            text += f"The cartegories we do not have data on include {', '.join(missing_cats)}. "

    mean_percentage = df.groupby("econ")["percentage"].mean().reset_index()
    n = 3
    top_econs = mean_percentage.sort_values(by="percentage", ascending=False).head(n)
    text += f"On average, the top {n} spending economic categories are "
    text += format_econ_cats_with_numbers(top_econs, format_percentage)
    text += "; "

    bottom_econs = mean_percentage.sort_values(by="percentage", ascending=True).head(n)
    text += f"while the bottom {n} spenders are "
    text += format_econ_cats_with_numbers(bottom_econs, format_percentage)
    text += ". "

    std_percentage = df.groupby("econ")["percentage"].std().reset_index()
    m = 2
    stable_econs = std_percentage.sort_values(by="percentage", ascending=True).head(m)
    text += f"Relatively, public expenditure remain the most stable in "
    text += format_econ_cats_with_numbers(stable_econs, format_std)
    text += "; "

    flux_econs = std_percentage.sort_values(by="percentage", ascending=False).head(m)
    text += f"while spending in "
    text += format_econ_cats_with_numbers(flux_econs, format_std)
    text += f" fluctuate the most over time. "

    return text


def format_econ_cats_with_numbers(df, format_number_func):
    return format_cats_with_numbers(df, format_econ_cat, format_number_func)


def format_econ_cat(row):
    return ECON_CAT_MAP[row["econ"]]


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
    if not data or not country:
        return {"display": "block"}, {}, 0, 0, 0, {}
    try:
        country_info = server_store.get("basic_country_info")
        expenditure_years = country_info[country].get("expenditure_years", [])
        poverty_years = country_info[country].get("poverty_years", [])

        slider_configs = get_slider_config(expenditure_years, poverty_years)
        return slider_configs
    except (KeyError, TypeError, ValueError):
        return {"display": "block"}, {}, 0, 0, 0, {}


@callback(
    Output("subnational-spending", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("expenditure-plot-radio", "value"),
    Input("year-slider", "value"),
    Input("stored-data-subnat-boundaries", "data"),
    State("theme-store", "data"),
)
def render_subnational_spending_figures(data, country_data, country, plot_type, year, subnat_boundaries, theme):
    if year is None or not data or not country_data or not country:
        return empty_plot("Data not available")
    if not subnat_boundaries:
        return empty_plot("Data not available")

    geojson = server_store.get("subnat_boundaries")
    disputed_geojson = filter_geojson_by_country(server_store.get("disputed_boundaries"), country)
    lat, lon = [
        server_store.get("basic_country_info")[country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = server_store.get("basic_country_info")[country]["zoom"]

    filtered_geojson = filter_geojson_by_country(geojson, country)
    df = server_store.get("geo1_expenditure")
    df = filter_country_sort_year(df, country)
    df = df[df.adm1_name != "Central Scope"]
    currency_code = server_store.get("basic_country_info")[country]["currency_code"]
    add_currency_column(df, 'expenditure', currency_code)
    add_currency_column(df, 'per_capita_expenditure', currency_code)

    if df.empty or year not in df.year.unique():
        return empty_plot("No expenditure data available for the selected year")

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
        )


@callback(
    Output("subnational-poverty", "figure"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider", "value"),
    Input("stored-data-subnat-boundaries", "data"),
    State("theme-store", "data"),
)
def render_subnational_poverty_figure(subnational_data, country_data, country, year, subnat_boundaries, theme):
    if year is None or not subnational_data or not country_data or not country:
        return empty_plot("Data not available")
    if not subnat_boundaries:
        return empty_plot("Data not available")

    geojson = server_store.get("subnat_boundaries")
    disputed_geojson = filter_geojson_by_country(
        server_store.get("disputed_boundaries"), country
    )
    filtered_geojson = filter_geojson_by_country(geojson, country)
    df = server_store.get("subnational_poverty_rate")
    df = filter_country_sort_year(df, country)

    legend_min, legend_max = server_store.get("basic_country_info")[country].get(
        "poverty_bounds", (None, None)
    )
    lat, lon = [
        server_store.get("basic_country_info")[country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = server_store.get("basic_country_info")[country]["zoom"]

    available_years = server_store.get("basic_country_info")[country].get(
        "poverty_years", []
    )
    relevant_years = [x for x in available_years if x <= year]

    if not relevant_years or df.empty:
        return empty_plot("Poverty data not available for this time period")

    income_level = server_store.get("basic_country_info")[country].get("income_level")
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
    )


@callback(
    Output("subnational-spending-narrative", "children"),
    Input("stored-data-subnational", "data"),
    Input("stored-basic-country-data", "data"),
    Input("country-select", "value"),
    Input("year-slider", "value"),
)
def render_subnational_spending_narrative(
    subnational_data, country_data, country, year
):
    if year is None or not subnational_data or not country_data or not country:
        return "Data not available"

    df_poverty = server_store.get("subnational_poverty_rate")
    df_poverty = filter_country_sort_year(df_poverty, country)

    available_years = server_store.get("basic_country_info")[country].get(
        "poverty_years", []
    )
    currency_code = server_store.get("basic_country_info")[country]["currency_code"]
    relevant_years = [x for x in available_years if x <= year]

    if not relevant_years or df_poverty.empty:
        df_poverty = pd.DataFrame()

    df_spending = server_store.get("geo1_expenditure")
    df_spending = filter_country_sort_year(df_spending, country)
    df_spending = df_spending[
        (df_spending.adm1_name != "Central Scope") & (df_spending.year == year)
    ]

    if df_spending.empty:
        return "No spending data available"

    return subnational_spending_narrative(df_spending, df_poverty, currency_code)


@callback(
    Output("pefa-narrative", "children"),
    Output("pefa-overall", "figure"),
    Output("pefa-by-pillar", "figure"),
    Input("stored-data", "data"),
    Input("stored-data-pefa", "data"),
    Input("country-select", "value"),
)
def render_pefa_overall(data, pefa_data, country):
    if not pefa_data or not data or not country:
        return dash.no_update, dash.no_update, dash.no_update

    pefa_df = server_store.get("pefa")
    country_pefa_df = filter_country_sort_year(pefa_df, country)

    all_countries_pov = server_store.get("expenditure_w_poverty")
    country_pov_df = filter_country_sort_year(all_countries_pov, country)

    return (
        pefa.pefa_narrative(country_pefa_df),
        pefa.pefa_overall_figure(country_pefa_df, country_pov_df),
        pefa.pefa_pillar_heatmap(country_pefa_df),
    )


@callback(
    Output("func-growth", "figure"),
    Output("func-growth-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("country-select", "value"),
    Input("budget-increment-radio", "value"),
)
def render_budget_func_changes(data, country, exp_type):
    return budget_increment_analysis.render_fig_and_narrative(data, country, exp_type)
