import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import traceback
from dash import html
from components.year_slider import get_slider_config
from translations import t, genitive, locative, elide_que
from constants import translate_func_sub
from viz_theme import (
    DIVERGING, CENTRAL_COLOR, REGIONAL_COLOR, TREEMAP_PALETTE,
    get_map_colorscale, darken_color, lighten_color, add_opacity,
)
from utils import (
    add_currency_column,
    add_disputed_overlay,
    empty_plot,
    filter_country_sort_year,
    filter_geojson_by_country,
    format_currency,
    generate_error_prompt,
    get_correlation_text,
    millify,
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


def render_func_subnat_overview(func_econ_data, sub_func_data, country, selected_year, func, currency_code, lang="en"):
    if not func_econ_data or not sub_func_data or not country:
        return (
            empty_plot(t("loading", lang)),
            empty_plot(t("loading", lang)),
            t("loading", lang),
        )

    data_by_func_admin0 = _subset_data(
        func_econ_data['expenditure_by_country_func_year'], selected_year, country, func
    )

    data_by_func_sub_geo0 = _subset_data(
        sub_func_data["expenditure_by_country_sub_func_year"],
        selected_year, country, func
    ).sort_values(by='func_sub')

    if data_by_func_admin0.empty and data_by_func_sub_geo0.empty:
        return (
            empty_plot(t("error.no_data_period", lang)),
            empty_plot(t("error.no_data_period", lang)),
            generate_error_prompt("DATA_UNAVAILABLE", lang=lang),
        )

    fig1 = _central_vs_regional_fig(data_by_func_sub_geo0, func, currency_code, lang=lang)
    fig2 = _sub_func_fig(data_by_func_sub_geo0, func, currency_code, lang=lang)

    narrative = _sub_func_narrative(
        data_by_func_admin0, data_by_func_sub_geo0, country, selected_year, func, lang=lang
    )
    return fig1, fig2, narrative

def _subset_data(stored_data, year, country, func):
    data = pd.DataFrame(stored_data)
    data = filter_country_sort_year(data, country)
    return data.loc[(data.func == func) & (data.year == year)]

def _central_vs_regional_fig(data, func, currency_code, lang="en"):
    func_lower = t(f"sector.{func.lower()}", lang)
    fig_title = t(
        "chart.func_spending_directed", lang,
        func=func_lower, func_gen=genitive(lang, func_lower),
    )
    central_vs_regional = (
        data.groupby("geo0").sum(numeric_only=True).reset_index()
    )
    if central_vs_regional.empty:
        return empty_plot(t("error.no_data_period", lang), fig_title)

    add_currency_column(central_vs_regional, 'real_expenditure', currency_code)
    # Translate the slice labels: "Central" → "Central" (same in FR),
    # "Regional" → "Régional". Unknown values pass through unchanged.
    geo0_key_map = {"Central": "trace.central", "Regional": "trace.regional"}
    pie_labels = [
        t(geo0_key_map[g], lang) if g in geo0_key_map else g
        for g in central_vs_regional["geo0"]
    ]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=pie_labels,
                values=central_vs_regional["real_expenditure"],
                hole=0.5,
                marker=dict(colors=[CENTRAL_COLOR, REGIONAL_COLOR]),
                customdata=np.stack(central_vs_regional["real_expenditure_formatted"]),
                hovertemplate="<b>" + t("hover.real_expenditure", lang) + "</b>: %{customdata}<br>"
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


def _sub_func_fig(data, func, currency_code, lang="en"):
    func_lower = t(f"sector.{func.lower()}", lang)
    fig_title = t(
        "chart.func_levels_spending", lang,
        func=func_lower, func_gen=genitive(lang, func_lower),
    )
    education_values = data.groupby("func_sub", sort=False).sum(numeric_only=True).reset_index()

    if education_values.empty:
        return empty_plot(t("error.no_data_period", lang), fig_title)

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
        # IDs stay in raw English: they are internal identifiers for plotly's
        # treemap (parent/child linkage), not displayed to the user. The
        # visible label is translated separately.
        parent_totals[row.func_sub] = row.expenditure
        base_color = TREEMAP_PALETTE[i % len(TREEMAP_PALETTE)]
        parent_colors[row.func_sub] = base_color
        ids.append(row.func_sub)
        parents.append("")
        sub_label = translate_func_sub(row.func_sub, lang)
        labels.append(f"{sub_label}<br>{format_currency(row.expenditure, currency_code)} ({percent_of_total:.0f}%)")
        values.append(row.expenditure)
        hover_texts.append(f"{t('hover.real_expenditure', lang)}: {format_currency(row.real_expenditure, currency_code)}")
        colors.append(base_color)

    data_grouped = (
        data.groupby(["func_sub", "geo0"], sort=False).sum(numeric_only=True).reset_index()
    )

    # Maps raw geo0 data values ("Central" / "Regional") to their
    # translation keys. Other values fall through untranslated.
    geo0_key_map = {"Central": "trace.central", "Regional": "trace.regional"}

    for _, row in data_grouped.iterrows():
        parent = row["func_sub"]
        percent_of_parent = (row["expenditure"] / parent_totals[parent]) * 100 \
                if parent_totals[parent] > 0 else 0

        ids.append(f"{row['func_sub']} - {row['geo0']}")
        parents.append(parent)
        values.append(row["expenditure"])
        geo0_key = geo0_key_map.get(row["geo0"])
        geo0_label = t(geo0_key, lang) if geo0_key else row["geo0"]
        labels.append(f"{geo0_label}<br>{format_currency(row['expenditure'], currency_code)} ({percent_of_parent:.0f}%)")
        hover_texts.append(f"{t('hover.real_expenditure', lang)}: {format_currency(row['real_expenditure'], currency_code)}")
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

def _sub_func_narrative(data_by_func_admin0, data_by_func_sub_geo0, country, selected_year, func, lang="en"):
    try:
        total_spending = data_by_func_sub_geo0["real_expenditure"].sum()
        regional_spending = data_by_func_sub_geo0[
            data_by_func_sub_geo0.geo0 == 'Regional'
        ].real_expenditure.sum()
        geo_tagged = regional_spending / total_spending * 100
        decentralization = data_by_func_admin0.expenditure_decentralization.values[0] * 100

        func_name = t(f"sector.{func.lower()}", lang)
        func_gen = genitive(lang, func_name)

        country_display = t(f"country.{country}", lang)
        text = t("narrative.subnat_intro", lang,
                 country=country_display,
                 country_loc=locative(lang, country_display),
                 year=selected_year)

        subnat_exp_available = not math.isnan(decentralization) and not math.isclose(decentralization, 0)
        geo_exp_available = not math.isnan(geo_tagged) and not math.isclose(geo_tagged, decentralization)
        if subnat_exp_available and geo_exp_available:
            text += t("narrative.subnat_decentralized", lang, pct=decentralization, func=func_name, func_gen=func_gen)
            text += t("narrative.subnat_geo_available", lang, pct=geo_tagged, func=func_name, func_gen=func_gen)
        elif subnat_exp_available and not geo_exp_available:
            text += t("narrative.subnat_decentralized", lang, pct=decentralization, func=func_name, func_gen=func_gen)
            text += t("narrative.subnat_geo_unavailable", lang)
        elif not subnat_exp_available and geo_exp_available:
            text += t("narrative.subnat_no_data", lang, func=func_name, func_gen=func_gen)
            text += t("narrative.subnat_geo_available", lang, pct=geo_tagged, func=func_name, func_gen=func_gen)
        else:
            text += t("narrative.subnat_no_level_data", lang, func=func_name, func_gen=func_gen)
    except:
        traceback.print_exc()
        return generate_error_prompt("GENERIC_ERROR", lang=lang)

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
    lang="en",
):

    if (
        not subnational_data
        or not country_data
        or not country
        or year is None
    ):
        return empty_plot(t("error.data_not_available", lang))

    currency_code = country_data['basic_country_info'][country]['currency_code']
    df = _subset_data(
        subnational_data['expenditure_and_outcome_by_country_geo1_func_year'],
        year, country, func
    )
    df = df[df.adm1_name != 'Central Scope']

    if df.empty:
        return empty_plot(t("error.no_data_year", lang))

    if expenditure_type not in df.columns:
        return empty_plot(t("error.data_unavailable_named", lang, dataset_name=expenditure_type))

    geojson = subnat_boundaries[country]
    disputed_geojson = subnational_data['disputed_boundaries']
    filtered_geojson = filter_geojson_by_country(geojson, country)

    lat, lon = [
        country_data["basic_country_info"][country].get(k)
        for k in ["display_lat", "display_lon"]
    ]
    zoom = country_data["basic_country_info"][country]["zoom"]

    # Drop NaN values and format
    df = df.dropna(subset=[expenditure_type])
    add_currency_column(df, expenditure_type, currency_code)

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
        custom_data=[expenditure_type + '_formatted'],
        locations="adm1_name",
        featureidkey="properties.region",
        center={"lat": lat, "lon": lon},
        zoom=zoom,
        mapbox_style="carto-positron",
        hover_data={expenditure_type: False},
        color_continuous_scale=get_map_colorscale(theme),
    )

    # Add trace for regions without data
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
    # Map the expenditure_type data key (e.g. "per_capita_expenditure") to a
    # localized hover label. Previously this did `title()` on the snake_case
    # name, which leaked English ("Per Capita Expenditure") into FR hovers.
    exp_type_label_map = {
        "per_capita_expenditure": "hover.per_capita_spending",
        "expenditure": "hover.expenditure_label",
    }
    exp_type_label_key = exp_type_label_map.get(expenditure_type)
    exp_type_label = (
        t(exp_type_label_key, lang)
        if exp_type_label_key else expenditure_type.replace('_', ' ').title()
    )
    no_data_trace.hovertemplate = (
        f"<b>{t('hover.region', lang)}:</b> %{{location}}<br>"
        f"<b>{exp_type_label}:</b> {t('hover.data_not_available', lang)}<extra></extra>"
    )
    fig.add_trace(no_data_trace)

    fig.data[0].hovertemplate = (
        f"<b>{t('hover.region', lang)}:</b> %{{location}}<br>"
        f"<b>{exp_type_label}:</b> %{{customdata[0]}}<extra></extra>"
    )
    add_disputed_overlay(fig, disputed_geojson, zoom, lang=lang)

    cofog_name = t(f"cofog.{func.lower()}", lang)
    fig.update_layout(
        title=t(
            "chart.subnational_func_spending", lang,
            func=cofog_name, func_gen=genitive(lang, cofog_name),
        ),
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
                text=t("annotation.displaying_data_from", lang, year=year),
                showarrow=False,
                font=dict(size=12),
            ),
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.2,
                xanchor="left",
                text=t("source.boost_database", lang),
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

FUNC_OUTCOME_KEY_MAP = {
    'Education': 'outcome.school_attendance',
    'Health': 'outcome.uhc_index',
}

def update_hd_index_map(
    subnational_data, country_data, country, year, subnat_boundaries, func, theme,
    lang="en",
):
    if (
        not subnational_data
        or not country_data
        or not country
        or year is None
    ):
        return empty_plot(t("error.data_not_available", lang))

    all_data = pd.DataFrame(
        subnational_data["expenditure_and_outcome_by_country_geo1_func_year"]
    )
    all_data = filter_country_sort_year(all_data, country)
    all_data = all_data[(all_data.func == func) & (all_data.adm1_name != 'Central Scope')]

    outcome_data = all_data.dropna(subset=["outcome_index"])
    available_years = sorted(outcome_data["year"].unique())
    relevant_years = [y for y in available_years if y <= year]

    if not relevant_years:
        return empty_plot(t("error.no_outcome_data", lang))

    display_year = relevant_years[-1]
    df = all_data[all_data.year == display_year].copy()

    if df.empty:
        return empty_plot(t("error.no_data_year", lang))

    outcome_name_key = FUNC_OUTCOME_KEY_MAP.get(func)
    outcome_name = t(outcome_name_key, lang) if outcome_name_key else FUNC_OUTCOME_MAP[func][0]
    _, transform_fn, format_fn = FUNC_OUTCOME_MAP[func]
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
    df = df.dropna(subset=["outcome_index"])
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
        color_continuous_scale=get_map_colorscale(theme),
    )

    formatted_outcome_index = df['outcome_index'].map(format_fn).values
    fig.update_traces(
        customdata=formatted_outcome_index,
        hovertemplate="<b>" + t("hover.region", lang) + ":</b> %{location}<br>"
            + f"<b>{outcome_name}:</b> " + "%{customdata}<br>"
            + "<extra></extra>",
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
    no_data_trace.hovertemplate = (
        f"<b>{t('hover.region', lang)}:</b> %{{location}}<br>"
        f"<b>{outcome_name}:</b> {t('hover.data_not_available', lang)}<extra></extra>"
    )
    fig.add_trace(no_data_trace)

    formatted_outcome_index = df['outcome_index'].map(format_fn).values
    fig.data[0].customdata = formatted_outcome_index
    fig.data[0].hovertemplate = (
        "<b>" + t("hover.region", lang) + ":</b> %{location}<br>"
        + f"<b>{outcome_name}:</b> " + "%{customdata}<extra></extra>"
    )
    add_disputed_overlay(fig, disputed_geojson, zoom, lang=lang)

    fig.update_layout(
        title=t("chart.subnational_outcome", lang, outcome_name=outcome_name),
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
                text=t("annotation.displaying_data_from", lang, year=display_year),
                showarrow=False,
                font=dict(size=12),
            ),
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.2,
                xanchor="left",
                text=t("source.undp_gdl", lang),
                showarrow=False,
                font=dict(size=12),
            ),
        ],
    )

    return fig


def render_func_subnat_rank(subnational_data, country, base_year, func, currency_code, lang="en"):
    if not subnational_data or not country:
        return empty_plot(t("loading", lang)), t("loading", lang)

    data = _subset_data(
        subnational_data["expenditure_and_outcome_by_country_geo1_func_year"],
        base_year, country, func
    )
    data = data[data["outcome_index"].notna() & data["per_capita_expenditure"].notna()]
    data = filter_country_sort_year(data, country)
    if data.empty:
        return empty_plot(
            t("error.no_outcome_data", lang)
        ), generate_error_prompt("DATA_UNAVAILABLE", lang=lang)

    outcome_name_key = FUNC_OUTCOME_KEY_MAP.get(func)
    outcome_name = t(outcome_name_key, lang) if outcome_name_key else FUNC_OUTCOME_MAP[func][0]
    _, transform_fn, format_fn = FUNC_OUTCOME_MAP[func]
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
                hovertemplate="<b>" + t("hover.expenditure_label", lang) + ":</b> %{source.customdata[0]}<br>"
                + f"<b>{outcome_name}:</b> " + "%{target.customdata[0]}<br>"
                + "<extra></extra>",
            ),
        )
    )

    per_capita_label = t("label.per_capita_expenditure_on", lang, func=t(f"cofog.{func.lower()}", lang))
    fig.add_annotation(
        x=0.1,
        y=1,
        arrowcolor="rgba(0, 0, 0, 0)",
        text=f"<b>{per_capita_label}</b><br> <b>{base_year}</b>",
    )
    fig.add_annotation(
        x=0.9,
        y=1,
        arrowcolor="rgba(0, 0, 0, 0)",
        text=f"<b>{outcome_name}</b> <br> <b>{base_year}</b>",
    )

    rank_keys = {0: "rank.1st", 10: "rank.10th", 20: "rank.20th", 30: "rank.30th", 40: "rank.40th"}
    for i in range(0, n + 1, 10):
        rank_key = rank_keys.get(i)
        if rank_key:
            fig.add_annotation(
                y=1 - ((i + 1) / (n + 1)),
                x=0.075,
                yshift=10,
                text=f"<b>{t(rank_key, lang)}</b>",
                showarrow=False,
            )

    narrative = _func_subnat_rank_narrative(base_year, func, data, lang=lang)
    return fig, narrative


def _func_subnat_rank_narrative(year, func, data, lang="en"):
    func_lower = t(f"sector.{func.lower()}", lang)

    outcome_name_key = FUNC_OUTCOME_KEY_MAP.get(func)
    outcome_name = t(outcome_name_key, lang) if outcome_name_key else FUNC_OUTCOME_MAP[func][0]
    outcome_name_lower = re.sub(r'\buhc\b', 'UHC', outcome_name.lower(), flags=re.IGNORECASE)

    # For the correlation narrative, pass articled display names so the
    # generated French reads "entre les dépenses... et l'indice UHC..."
    # rather than the ungrammatical bare-noun concatenation.
    outcome_display = (
        t(f"{outcome_name_key}.narrative", lang)
        if outcome_name_key else outcome_name_lower
    )
    PCC = get_correlation_text(
        data,
        {
            "col_name": "outcome_index",
            "display": outcome_display,
        },
        {
            "col_name": "per_capita_expenditure",
            "display": t("label.per_capita_expenditure_lower_on", lang, func=func_lower),
        },
        lang=lang,
    )

    narrative = t("narrative.subnat_rank_year", lang, year=year, pcc=PCC)
    data["ROI"] = data.outcome_index / data.per_capita_expenditure
    best_ROI = data[data["ROI"] == data.ROI.max()].adm1_name.values[0]
    worst_ROI = data[data["ROI"] == data.ROI.min()].adm1_name.values[0]

    # Use the .narrative form (with definite article in French) for
    # mid-sentence interpolation — "mesuré par l'indice UHC" not
    # "mesuré par indice UHC".
    outcome_narrative = (
        t(f"{outcome_name_key}.narrative", lang)
        if outcome_name_key else outcome_name_lower
    )
    narrative += t(
        "narrative.subnat_rank_roi", lang,
        func=func_lower, outcome_name=outcome_narrative,
        best=best_ROI, worst=worst_ROI,
        # que_worst handles elision of "que" before a vowel-initial region
        # name ("tandis qu'Afar") in French. English template ignores it.
        que_worst=elide_que(lang, worst_ROI),
    )
    return narrative
