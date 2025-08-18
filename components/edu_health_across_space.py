import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import traceback
from dash import html
from components.year_slider import get_slider_config
from utils import (
    add_disputed_overlay,
    empty_plot,
    filter_country_sort_year,
    filter_geojson_by_country,
    generate_error_prompt,
    get_correlation_text,
    millify,
    add_opacity,
)


def update_year_slider(data, country, func):
    data = pd.DataFrame(data["expenditure_and_outcome_by_country_geo1_func_year"])
    data = data.loc[(data.func == func)]

    data = filter_country_sort_year(data, country)

    if data.empty:
        return {"display": "block"}, {}, 0, 0, 0, {}

    expenditure_years = list(data.year.astype("int").unique())
    data = data[data["outcome_index"].notna()]
    outcome_years = list(data.year.astype("int").unique())
    return get_slider_config(expenditure_years, outcome_years)


def render_func_subnat_overview(func_econ_data, sub_func_data, country, selected_year, func):
    if not func_econ_data or not sub_func_data or not country:
        return

    data_by_func_admin0 = _subset_data(
        func_econ_data['expenditure_by_country_func_year'], selected_year, country, func
    )

    data_by_func_sub_geo0 = _subset_data(
        sub_func_data["expenditure_by_country_sub_func_year"], 
        selected_year, country, func
    ).sort_values(by='func_sub')

    if data_by_func_admin0.empty and data_by_func_sub_geo0.empty:
        return (
            empty_plot("No data available for this period"),
            empty_plot("No data available for this period"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    fig1 = _central_vs_regional_fig(data_by_func_sub_geo0, func)
    fig2 = _sub_func_fig(data_by_func_sub_geo0, func)

    narrative = _sub_func_narrative(
        data_by_func_admin0, data_by_func_sub_geo0, country, selected_year, func
    )
    return fig1, fig2, narrative

def _subset_data(stored_data, year, country, func):
    data = pd.DataFrame(stored_data)
    data = filter_country_sort_year(data, country)
    return data.loc[(data.func == func) & (data.year == year)]

def _central_vs_regional_fig(data, func):
    fig_title = f"Where was {func.lower()} spending directed?"
    central_vs_regional = (
        data.groupby("geo0").sum(numeric_only=True).reset_index()
    )
    if central_vs_regional.empty:
        return empty_plot("No data available for this period", fig_title)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=central_vs_regional["geo0"],
                values=central_vs_regional["real_expenditure"],
                hole=0.5,
                marker=dict(colors=["rgb(17, 141, 255)", "rgb(160, 209, 255)"]),
                customdata=[
                    millify(x)
                    for x in np.stack(central_vs_regional["real_expenditure"])
                ],
                hovertemplate="<b>Real expenditure</b>: $%{customdata}<br>"
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

def _sub_func_fig(data, func):
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
    parent_totals = {}
    for _, row in education_values.iterrows():
        percent_of_total = (row["expenditure"] / total) * 100
        parent_totals[row["func_sub"]] = row["expenditure"]
        ids.append(row["func_sub"])
        parents.append("")
        labels.append(f"{row['func_sub']}<br>{millify(row['expenditure'])} ({percent_of_total:.0f}%)")
        values.append(row["expenditure"])
        hover_texts.append(f"Real expenditure: {millify(row['real_expenditure'])}")

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

        labels.append(f"{row['geo0']}<br>{millify(row['expenditure'])} ({percent_of_parent:.0f}%)")
        hover_texts.append(f"Real expenditure: {millify(row['real_expenditure'])}")

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
):
    if (
        not subnational_data
        or not country_data
        or not country
        or year is None
    ):
        return empty_plot("Data not available")

    df = _subset_data(
        subnational_data['expenditure_and_outcome_by_country_geo1_func_year'],
        year, country, func
    )
    df = df[df.adm1_name != 'Central Scope']

    if df.empty:
        return empty_plot("No data available for the selected year")

    if expenditure_type not in df.columns:
        return empty_plot(f"{expenditure_type} data not available")

    geojson = subnat_boundaries[country]
    disputed_geojson = subnational_data['disputed_boundaries']
    filtered_geojson = filter_geojson_by_country(geojson, country)

    lat, lon = [
        country_data["basic_country_info"][country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = country_data["basic_country_info"][country]["zoom"]

    # Identify regions without data
    all_regions = [
        feature["properties"]["region"] for feature in filtered_geojson["features"]
    ]
    regions_without_data = [r for r in all_regions if r not in df.adm1_name.values]
    df_no_data = pd.DataFrame({"region_name": regions_without_data})
    df_no_data["adm1_name"] = None

    fig = px.choropleth_mapbox(
        df,
        geojson=filtered_geojson,
        color=expenditure_type,
        locations="adm1_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        zoom=zoom,
        mapbox_style="carto-positron",
    )

    no_data_trace = px.choropleth_mapbox(
        df_no_data,
        geojson=filtered_geojson,
        color_discrete_sequence=["rgba(211, 211, 211, 0.3)"],
        locations="region_name",
        featureidkey="properties.region",
        zoom=zoom,
    ).data[0]

    no_data_trace.legendgroup = "no-data"
    no_data_trace.showlegend = False 
    fig.add_trace(no_data_trace)

    hover_template_str = (
        "<b>Region:</b> %{location}<br>"
        f"<b>{expenditure_type.replace('_', ' ').title()}:</b> %{{z:,.2f}}<br>"
        "<extra></extra>"
    )

    fig.update_traces(hovertemplate=hover_template_str)
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
    subnational_data, country_data, country, year, subnat_boundaries, func,
):
    if (
        not subnational_data
        or not country_data
        or not country
        or year is None
    ):
        return empty_plot("Data not available")

    df = _subset_data(
        subnational_data["expenditure_and_outcome_by_country_geo1_func_year"],
        year, country, func
    )
    df = df[df.adm1_name != 'Central Scope']

    if df.empty:
        return empty_plot("No data available for the selected year")

    outcome_name, transform_fn, format_fn = FUNC_OUTCOME_MAP[func]
    df['outcome_index'] = df['outcome_index'].map(transform_fn)

    geojson = subnat_boundaries[country]
    filtered_geojson = filter_geojson_by_country(geojson, country)

    disputed_geojson = subnational_data['disputed_boundaries']

    lat, lon = [
        country_data["basic_country_info"][country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = country_data["basic_country_info"][country]["zoom"]

    # Identify regions without data
    all_regions = [
        feature["properties"]["region"] for feature in filtered_geojson["features"]
    ]
    regions_without_data = [r for r in all_regions if r not in df.adm1_name.values]
    df_no_data = pd.DataFrame({"region_name": regions_without_data})
    df_no_data["adm1_name"] = None

    # Create the choropleth for outcome index
    fig = px.choropleth_mapbox(
        df,
        geojson=filtered_geojson,
        color="outcome_index",
        locations="adm1_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        zoom=zoom,
        mapbox_style="carto-positron",
    )

    no_data_trace = px.choropleth_mapbox(
        df_no_data,
        geojson=filtered_geojson,
        color_discrete_sequence=["rgba(211, 211, 211, 0.3)"],
        locations="region_name",
        featureidkey="properties.region",
        zoom=zoom,
    ).data[0]
    no_data_trace.legendgroup = "no-data"
    no_data_trace.showlegend = False 
    fig.add_trace(no_data_trace)

    formatted_outcome_index = df['outcome_index'].map(format_fn).values
    fig.update_traces(
        customdata=formatted_outcome_index,
        hovertemplate="<b>Region:</b> %{location}<br>"
            + f"<b>{outcome_name}:</b> " + "%{customdata}<br>"
            + "<extra></extra>",
    )
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
                text="Source: UNDP through Global Data Lab",
                showarrow=False,
                font=dict(size=12),
            ),
        ],
    )

    return fig


def render_func_subnat_rank(subnational_data, country, base_year, func):
    if not subnational_data or not country:
        return

    data = _subset_data(
        subnational_data["expenditure_and_outcome_by_country_geo1_func_year"], 
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
            f"${millify(data_expenditure_sorted.iloc[i]['per_capita_expenditure'])}",
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

    color_highs = px.colors.sequential.Oranges[-1 * gradient_n :]
    colors_lows = px.colors.sequential.Blues[-1 * gradient_n :]
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


