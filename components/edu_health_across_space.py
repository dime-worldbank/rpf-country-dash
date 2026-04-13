import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import traceback
from dash import html
from components.year_slider import get_slider_config
from viz_theme import (
    DIVERGING, CENTRAL_COLOR, REGIONAL_COLOR, TREEMAP_PALETTE,
    get_map_colorscale, darken_color, lighten_color, add_opacity,
)
import server_cache
from utils import (
    add_currency_column,
    add_disputed_overlay,
    empty_plot,
    filter_country_sort_year,
    filter_geojson_by_country,
    subset_geojson_by_regions,
    format_currency,
    generate_error_prompt,
    get_correlation_text,
    millify,
)


def update_year_slider(data, country, func):
    data = server_cache.get("geo1_func_expenditure")
    data = data.loc[(data.func == func)]

    data = filter_country_sort_year(data, country)

    if data.empty:
        return {"display": "block"}, {}, 0, 0, 0, {}

    expenditure_years = list(data.year.astype("int").unique())
    data = data[data["outcome_index"].notna()]
    outcome_years = list(data.year.astype("int").unique())
    return get_slider_config(expenditure_years, outcome_years)


def render_func_subnat_overview(func_econ_data, sub_func_data, country, selected_year, func, currency_code):
    if not func_econ_data or not sub_func_data or not country:
        return (
            empty_plot("Loading..."),
            empty_plot("Loading..."),
            "Loading...",
        )

    data_by_func_admin0 = _subset_data(
        server_cache.get("func_by_country_year"), selected_year, country, func
    )

    data_by_func_sub_geo0 = _subset_data(
        server_cache.get("sub_func_expenditure"),
        selected_year, country, func
    ).sort_values(by='func_sub')

    if data_by_func_admin0.empty and data_by_func_sub_geo0.empty:
        return (
            empty_plot("No data available for this period"),
            empty_plot("No data available for this period"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    fig1 = _central_vs_regional_fig(data_by_func_sub_geo0, func, currency_code)
    fig2 = _sub_func_fig(data_by_func_sub_geo0, func, currency_code)

    narrative = _sub_func_narrative(
        data_by_func_admin0, data_by_func_sub_geo0, country, selected_year, func
    )
    return fig1, fig2, narrative

def _subset_data(df, year, country, func):
    data = filter_country_sort_year(df, country)
    return data.loc[(data.func == func) & (data.year == year)]

def _central_vs_regional_fig(data, func, currency_code):
    fig_title = f"Where was {func.lower()} spending directed?"
    central_vs_regional = (
        data.groupby("geo0").sum(numeric_only=True).reset_index()
    )
    if central_vs_regional.empty:
        return empty_plot("No data available for this period", fig_title)

    add_currency_column(central_vs_regional, 'real_expenditure', currency_code)
    fig = go.Figure(
        data=[
            go.Pie(
                labels=central_vs_regional["geo0"],
                values=central_vs_regional["real_expenditure"],
                hole=0.5,
                marker=dict(colors=[CENTRAL_COLOR, REGIONAL_COLOR]),
                customdata=np.stack(central_vs_regional["real_expenditure_formatted"]),
                hovertemplate="<b>Real expenditure</b>: %{customdata}<br>"
                + "<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=fig_title,
        showlegend=True,
        plot_bgcolor="white",
    )
    return fig


def _sub_func_fig(data, func, currency_code):
    fig_title = f"How much did the gov spend on different levels of {func.lower()}?"
    education_values = data.groupby("func_sub", sort=False).sum(numeric_only=True).reset_index()

    if education_values.empty:
        return empty_plot("No data available for this period", fig_title)

    fig = go.Figure()
    total = data.expenditure.sum()
    ids = []
    parents = []
    labels = []
    values = []
    hover_texts = []
    colors = []
    parent_totals = {}
    parent_colors = {}

    for i, row in enumerate(education_values.itertuples()):
        percent_of_total = (row.expenditure / total) * 100
        parent_totals[row.func_sub] = row.expenditure
        base_color = TREEMAP_PALETTE[i % len(TREEMAP_PALETTE)]
        parent_colors[row.func_sub] = base_color
        ids.append(row.func_sub)
        parents.append("")
        labels.append(f"{row.func_sub}<br>{format_currency(row.expenditure, currency_code)} ({percent_of_total:.0f}%)")
        values.append(row.expenditure)
        hover_texts.append(f"Real expenditure: {format_currency(row.real_expenditure, currency_code)}")
        colors.append(base_color)

    data_grouped = (
        data.groupby(["func_sub", "geo0"], sort=False).sum(numeric_only=True).reset_index()
    )

    for _, row in data_grouped.iterrows():
        parent = row["func_sub"]
        percent_of_parent = (row["expenditure"] / parent_totals[parent]) * 100 \
                if parent_totals[parent] > 0 else 0

        ids.append(f"{row['func_sub']} - {row['geo0']}")
        parents.append(parent)
        values.append(row["expenditure"])
        labels.append(f"{row['geo0']}<br>{format_currency(row['expenditure'], currency_code)} ({percent_of_parent:.0f}%)")
        hover_texts.append(f"Real expenditure: {format_currency(row['real_expenditure'], currency_code)}")
        base_color = parent_colors[parent]
        if row["geo0"] == "Central":
            colors.append(darken_color(base_color, 0.75))
        else:
            colors.append(lighten_color(base_color, 0.35))

    fig.add_trace(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            textinfo="label",
            hovertemplate="<b>%{label}</b><br>%{customdata}<extra></extra>",
            customdata=hover_texts,
            marker=dict(colors=colors),
        )
    )

    fig.update_layout(
        autosize=True,
        plot_bgcolor="white",
        title=fig_title,
        margin=dict(l=15, r=15, b=15),
    )

    return fig

def _sub_func_narrative(data_by_func_admin0, data_by_func_sub_geo0, country, selected_year, func):
    try:
        total_spending = data_by_func_sub_geo0["real_expenditure"].sum()
        regional_spending = data_by_func_sub_geo0[
            data_by_func_sub_geo0.geo0 == 'Regional'
        ].real_expenditure.sum()
        geo_tagged = regional_spending / total_spending * 100
        decentralization = data_by_func_admin0.expenditure_decentralization.values[0] * 100

        func_name = func.lower()

        text = f"In {country}, as of {selected_year}, "

        subnat_exp_available_text = f"{decentralization:.1f}% of {func_name} spending is executed by regional or local governments (decentralized spending)"
        subnat_exp_not_available_text = f"we do not have data on {func_name} spending executed by regional or local governments (decentralized spending)"

        geo_exp_available_text = f", while {geo_tagged:.1f}% of {func_name} spending is geographically allocated, meaning it may be funded either centrally or regionally but is directed toward specific regions. To explore disparities in spending and {func_name} outcomes across subnational regions, we will focus on geographically allocated spending, as it provides a more complete picture of resources benefiting each region."
        geo_exp_not_available_text = ". However, data on geographically allocated spending – which would capture both central and regional spending benefiting specific locations — is not available. Ideally, we would use geographically allocated spending to analyze subnational disparities, but due to data limitations, we will use decentralized spending as a proxy."

        subnat_exp_available = not math.isnan(decentralization) and not math.isclose(decentralization, 0)
        geo_exp_available =  not math.isnan(geo_tagged) and not math.isclose(geo_tagged, decentralization)
        if subnat_exp_available and geo_exp_available:
            text += subnat_exp_available_text + geo_exp_available_text
        elif subnat_exp_available and not geo_exp_available:
            text += subnat_exp_available_text + geo_exp_not_available_text
        elif not subnat_exp_available and geo_exp_available:
            text += subnat_exp_not_available_text + geo_exp_available_text
        else:
            text += f"we do not have {func_name} spending at subnational level."
    except:
        traceback.print_exc()
        return generate_error_prompt("GENERIC_ERROR")

    return text


def update_func_expenditure_map(
    subnational_data,
    country_data,
    country,
    year,
    expenditure_type,
    subnat_boundaries,
    func,
    theme,
):

    if (
        not subnational_data
        or not country_data
        or not country
        or year is None
        or not subnat_boundaries
        or not subnat_boundaries.get(country)
    ):
        return empty_plot("Data not available")

    currency_code = server_cache.get("basic_country_info")[country]['currency_code']
    df = _subset_data(
        server_cache.get("geo1_func_expenditure"),
        year, country, func
    )
    df = df[df.adm1_name != 'Central Scope']

    if df.empty:
        return empty_plot("No data available for the selected year")

    if expenditure_type not in df.columns:
        return empty_plot(f"{expenditure_type} data not available")

    geojson = server_cache.get(f"subnat_boundaries:{country}")
    disputed_geojson = server_cache.get("disputed_boundaries")
    filtered_geojson = filter_geojson_by_country(geojson, country)

    lat, lon = [
        server_cache.get("basic_country_info")[country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = server_cache.get("basic_country_info")[country]["zoom"]

    # Drop NaN values and format
    df = df.dropna(subset=[expenditure_type])
    add_currency_column(df, expenditure_type, currency_code)

    all_regions = [
        feature["properties"]["region"] for feature in filtered_geojson["features"]
    ]
    regions_without_data = [r for r in all_regions if r not in df.adm1_name.values]

    fig = px.choropleth_mapbox(
        df,
        geojson=filtered_geojson,
        color=expenditure_type,
        custom_data=[expenditure_type + '_formatted'],
        locations="adm1_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        zoom=zoom,
        mapbox_style="carto-positron",
        hover_data={expenditure_type: False},
        color_continuous_scale=get_map_colorscale(theme),
    )

    if regions_without_data:
        df_no_data = pd.DataFrame({"region_name": regions_without_data})
        no_data_geojson = subset_geojson_by_regions(filtered_geojson, set(regions_without_data))
        no_data_trace = px.choropleth_mapbox(
            df_no_data,
            geojson=no_data_geojson,
            color_discrete_sequence=["rgba(211, 211, 211, 0.3)"],
            locations="region_name",
            featureidkey="properties.region",
            zoom=zoom,
        ).data[0]
        no_data_trace.showlegend = False
        no_data_trace.hovertemplate = f"<b>Region:</b> %{{location}}<br><b>{expenditure_type.replace('_', ' ').title()}:</b> Data not available<extra></extra>"
        fig.add_trace(no_data_trace)

    fig.data[0].hovertemplate = (
        "<b>Region:</b> %{location}<br>"
        f"<b>{expenditure_type.replace('_', ' ').title()}:</b> %{{customdata[0]}}<extra></extra>"
    )
    add_disputed_overlay(fig, disputed_geojson, zoom)

    fig.update_layout(
        title=f"Subnational {func} Spending",
        plot_bgcolor="white",
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
                text=f"Displaying data from {year}",
                showarrow=False,
                font=dict(size=12),
            ),
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.2,
                xanchor="left",
                text="Source: BOOST Database, World Bank",
                showarrow=False,
                font=dict(size=12),
            ),
        ],
    )

    return fig

FUNC_OUTCOME_MAP = {
    'Education': [
        'School Attendance for Age 6-17',
        lambda value: value * 100,
        lambda value: f"{value:.1f}%",
    ],
    'Health': [
        'UHC Index',
        lambda value: value,
        lambda value: f"{value:.2f}",
    ],
}
def update_hd_index_map(
    subnational_data, country_data, country, year, subnat_boundaries, func, theme,
):
    if (
        not subnational_data
        or not country_data
        or not country
        or year is None
        or not subnat_boundaries
        or not subnat_boundaries.get(country)
    ):
        return empty_plot("Data not available")

    all_data = server_cache.get("geo1_func_expenditure")
    all_data = filter_country_sort_year(all_data, country)
    all_data = all_data[(all_data.func == func) & (all_data.adm1_name != 'Central Scope')]

    outcome_data = all_data.dropna(subset=["outcome_index"])
    available_years = sorted(outcome_data["year"].unique())
    relevant_years = [y for y in available_years if y <= year]

    if not relevant_years:
        return empty_plot("No outcome data available for this period")

    display_year = relevant_years[-1]
    df = all_data[all_data.year == display_year].copy()

    if df.empty:
        return empty_plot("No data available for the selected year")

    outcome_name, transform_fn, format_fn = FUNC_OUTCOME_MAP[func]
    df['outcome_index'] = df['outcome_index'].map(transform_fn)

    geojson = server_cache.get(f"subnat_boundaries:{country}")
    filtered_geojson = filter_geojson_by_country(geojson, country)

    disputed_geojson = server_cache.get("disputed_boundaries")

    lat, lon = [
        server_cache.get("basic_country_info")[country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = server_cache.get("basic_country_info")[country]["zoom"]

    all_regions = [
        feature["properties"]["region"] for feature in filtered_geojson["features"]
    ]
    df = df.dropna(subset=["outcome_index"])
    regions_without_data = [r for r in all_regions if r not in df.adm1_name.values]

    fig = px.choropleth_mapbox(
        df,
        geojson=filtered_geojson,
        color="outcome_index",
        locations="adm1_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        zoom=zoom,
        mapbox_style="carto-positron",
        color_continuous_scale=get_map_colorscale(theme),
    )

    formatted_outcome_index = df['outcome_index'].map(format_fn).values
    fig.data[0].customdata = formatted_outcome_index
    fig.data[0].hovertemplate = (
        "<b>Region:</b> %{location}<br>"
        + f"<b>{outcome_name}:</b> " + "%{customdata}<extra></extra>"
    )

    if regions_without_data:
        df_no_data = pd.DataFrame({"region_name": regions_without_data})
        no_data_geojson = subset_geojson_by_regions(filtered_geojson, set(regions_without_data))
        no_data_trace = px.choropleth_mapbox(
            df_no_data,
            geojson=no_data_geojson,
            color_discrete_sequence=["rgba(211, 211, 211, 0.3)"],
            locations="region_name",
            featureidkey="properties.region",
            zoom=zoom,
        ).data[0]
        no_data_trace.showlegend = False
        no_data_trace.hovertemplate = f"<b>Region:</b> %{{location}}<br><b>{outcome_name}:</b> Data not available<extra></extra>"
        fig.add_trace(no_data_trace)
    add_disputed_overlay(fig, disputed_geojson, zoom)

    fig.update_layout(
        title=f"Subnational {outcome_name}",
        plot_bgcolor="white",
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
                text=f"Displaying data from {display_year}",
                showarrow=False,
                font=dict(size=12),
            ),
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.2,
                xanchor="left",
                text="Source: UNDP through Global Data Lab",
                showarrow=False,
                font=dict(size=12),
            ),
        ],
    )

    return fig


def render_func_subnat_rank(subnational_data, country, base_year, func, currency_code):
    if not subnational_data or not country:
        return empty_plot("Loading..."), "Loading..."

    data = _subset_data(
        server_cache.get("geo1_func_expenditure"),
        base_year, country, func
    )
    data = data[data["outcome_index"].notna() & data["per_capita_expenditure"].notna()]
    data = filter_country_sort_year(data, country)
    if data.empty:
        return empty_plot(
            "No outcome data available for this period"
        ), generate_error_prompt("DATA_UNAVAILABLE")

    outcome_name, transform_fn, format_fn = FUNC_OUTCOME_MAP[func]
    data['outcome_index'] = data['outcome_index'].map(transform_fn)

    n = data.shape[0]
    data_expenditure_sorted = data[["adm1_name", "per_capita_expenditure"]].sort_values(
        "per_capita_expenditure", ascending=False
    )
    data_outcome_sorted = data[["outcome_index", "adm1_name"]].sort_values(
        "outcome_index", ascending=False
    )
    source = list(data_expenditure_sorted.adm1_name)
    dest = list(data_outcome_sorted.adm1_name)
    node_custom_data = [
        (
            f"{format_currency(data_expenditure_sorted.iloc[i]['per_capita_expenditure'], currency_code)}",
            data_expenditure_sorted.iloc[i]["adm1_name"],
        )
        for i in range(n)
    ]
    node_custom_data += [
        (
            format_fn(data_outcome_sorted.iloc[i]['outcome_index']),
            data_outcome_sorted.iloc[i]["adm1_name"],
        )
        for i in range(n)
    ]

    gradient_n = 1 if n < 6 else 2 if n < 11 else 3

    color_highs = list(reversed(DIVERGING[:gradient_n]))
    colors_lows = DIVERGING[-gradient_n:]
    node_colors = (
        color_highs[::-1] + ["rgb(169,169,169)"] * (n - 2 * gradient_n) + colors_lows
    )
    node_colors_opaque = [add_opacity(color, 0.7) for color in node_colors]
    node_colors += [node_colors[source.index(dest[i])] for i in range(n)]

    fig = go.Figure()
    fig.add_trace(
        go.Sankey(
            node=dict(
                thickness=20,
                line=dict(color="black", width=0.2),
                label=list(source) + [name + "-" for name in list(dest)],
                y=[(i + 1) / (n + 1) for i in range(n)]
                + [(i + 1) / (n + 1) for i in range(n)],
                x=[0.1 for i in range(n)] + [0.9 for i in range(n)],
                color=node_colors,
                customdata=node_custom_data,
                hovertemplate="%{customdata[1]}:  %{customdata[0]}<extra></extra>",
            ),
            link=dict(
                source=[i for i in range(data.shape[0])],
                target=[data.shape[0] + dest.index(source[i]) for i in range(n)],
                color=node_colors_opaque,
                value=[1 for i in range(n)],
                hovertemplate="<b>Expenditure:</b> %{source.customdata[0]}<br>"
                + f"<b>{outcome_name}:</b> " + "%{target.customdata[0]}<br>"
                + "<extra></extra>",
            ),
        )
    )

    fig.add_annotation(
        x=0.1,
        y=1,
        arrowcolor="rgba(0, 0, 0, 0)",
        text=f"<b>Per Capita Expenditure on {func}</b><br> <b>{base_year}</b>",
    )
    fig.add_annotation(
        x=0.9,
        y=1,
        arrowcolor="rgba(0, 0, 0, 0)",
        text=f"<b>{outcome_name}</b> <br> <b>{base_year}</b>",
    )

    rank_mapping = {0: "1st", 10: "10th", 20: "20th", 30: "30th", 40: "40th"}
    for i in range(0, n + 1, 10):
        fig.add_annotation(
            y=1 - ((i + 1) / (n + 1)),
            x=0.075,
            yshift=10,
            text=f"<b>{rank_mapping[i]}</b>",
            showarrow=False,
        )

    narrative = _func_subnat_rank_narrative(base_year, func, data)
    return fig, narrative


def _func_subnat_rank_narrative(year, func, data):
    func_lower = func.lower()

    outcome_name, _, _ = FUNC_OUTCOME_MAP[func]
    outcome_name = re.sub(r'\buhc\b', 'UHC', outcome_name.lower(), flags=re.IGNORECASE)

    PCC = get_correlation_text(
        data,
        {
            "col_name": "outcome_index",
            "display": outcome_name,
        },
        {
            "col_name": "per_capita_expenditure",
            "display": f"per capita expenditure on {func_lower}",
        },
    )

    narrative = f"In {year}, {PCC}"
    data["ROI"] = data.outcome_index / data.per_capita_expenditure
    best_ROI = data[data["ROI"] == data.ROI.max()].adm1_name.values[0]
    worst_ROI = data[data["ROI"] == data.ROI.min()].adm1_name.values[0]

    narrative += f" Among the subnational regions, in terms of return on public spending on {func_lower} measured by {outcome_name}, {best_ROI} had the highest return on investment (ROI) while {worst_ROI} had the lowest."
    return narrative


