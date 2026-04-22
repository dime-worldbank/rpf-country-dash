import numpy as np
import pandas as pd
import plotly.graph_objects as go
from constants import FUNC_COLORS, translate_func
from translations import t
from utils import (
    filter_country_sort_year,
    empty_plot,
    generate_error_prompt,
    calculate_cagr,
)

DEFAULT_VISIBLE_CATEGORIES = [
    "Health",
    "Education",
    "General public services",
    "Overall budget",
]

NUM_YEARS = 5


def render_fig_and_narrative(data, country, exp_type, lang="en"):
    if not data:
        return empty_plot(t("loading", lang)), t("loading", lang)
    country_budget_changes_df = pd.DataFrame(data["expenditure_by_country_func_year"])
    country_budget_changes_df = filter_country_sort_year(
        country_budget_changes_df, country
    )
    country_budget_changes_df = country_budget_changes_df[
        country_budget_changes_df["domestic_funded_budget"].notna()
        & (round(country_budget_changes_df["domestic_funded_budget"]) != 0)
    ]

    overall_budget_df = country_budget_changes_df.groupby(
        ["country_name", "year"], as_index=False
    ).agg(
        {
            "budget": lambda x: x.sum(min_count=1),
            "domestic_funded_budget": lambda x: x.sum(min_count=1),
            "real_domestic_funded_budget": lambda x: x.sum(min_count=1),
        }
    )
    overall_budget_df["func"] = t("label.overall_budget", lang)

    # Now merge back into the dataframe
    country_budget_changes_df = pd.concat(
        [country_budget_changes_df, overall_budget_df], ignore_index=True
    )

    country_budget_changes_df = country_budget_changes_df.sort_values(
        ["country_name", "func", "year"]
    )

    end_year = country_budget_changes_df["year"].max()
    start_year = end_year - NUM_YEARS + 1
    # Take data from one year earlier to eb able to compute the YoY change for start_year as well
    full_years = list(range(start_year - 1, end_year + 1))
    all_funcs = country_budget_changes_df["func"].unique()
    # 'Fill' the full dataframe so that missing years will get Null values. This simplifies the calculation for YoY changes
    full_index = pd.MultiIndex.from_product(
        [all_funcs, full_years], names=["func", "year"]
    )
    full_df = pd.DataFrame(index=full_index).reset_index()

    country_budget_changes_df = full_df.merge(
        country_budget_changes_df, on=["func", "year"], how="left"
    )

    for col in ["domestic_funded_budget", "real_domestic_funded_budget"]:
        yoy_col = f"yoy_{col}"
        country_budget_changes_df.sort_values(["func", "year"], inplace=True)
        country_budget_changes_df[yoy_col] = (
            (
                country_budget_changes_df[col]
                - country_budget_changes_df.groupby("func")[col].shift(1)
            )
            / country_budget_changes_df.groupby("func")[col].shift(1)
        ) * 100
    # Restrict to data starting from start_year, and update the start_year value if that year has no data
    country_budget_changes_df = country_budget_changes_df[
        country_budget_changes_df.year >= start_year
    ]

    overall_label = t("label.overall_budget", lang)
    updated_start_year = country_budget_changes_df.loc[
        (country_budget_changes_df["func"] == overall_label)
        & country_budget_changes_df["domestic_funded_budget"].notna(),
        "year",
    ].min()
    selected_years = list(range(updated_start_year, end_year + 1))
    updated_num_years = end_year - updated_start_year + 1

    country_budget_changes_df = country_budget_changes_df[
        country_budget_changes_df.year.isin(selected_years)
    ]

    foreign_funding_isnull = (
        overall_budget_df["domestic_funded_budget"] == overall_budget_df["budget"]
    ).all()
    func_cagr_dict = {
        func: calculate_cagr(
            group.loc[group["year"] == updated_start_year, exp_type].sum(),
            group.loc[group["year"] == end_year, exp_type].sum(),
            updated_num_years,
        )
        for func, group in country_budget_changes_df.groupby("func")
    }
    valid_cagr_dict = {
        k: v for k, v in func_cagr_dict.items() if v is not None and not np.isnan(v)
    }

    if (not valid_cagr_dict) & (exp_type == "real_domestic_funded_budget"):
        return (
            empty_plot(t("error.inflation_adjusted_unavailable", lang)),
            generate_error_prompt(
                "DATA_UNAVAILABLE_DATASET_NAME",
                lang=lang,
                dataset_name="Inflation adjusted domestic funded budget",
            ),
        )
    fig = create_func_growth_figure(country_budget_changes_df, exp_type, lang=lang)

    highest_func_cat = max(
        (k for k in valid_cagr_dict if k != overall_label), key=valid_cagr_dict.get
    )
    other_candidates = [
        k for k in valid_cagr_dict if k != overall_label and k != highest_func_cat
    ]

    if other_candidates:
        lowest_func_cat = min(other_candidates, key=valid_cagr_dict.get)
    else:
        lowest_func_cat = highest_func_cat

    cagr_data = {
        "Overall budget": func_cagr_dict[overall_label],
        "highest": (highest_func_cat, func_cagr_dict[highest_func_cat]),
        "lowest": (lowest_func_cat, func_cagr_dict[lowest_func_cat]),
    }
    narrative = format_budget_increment_narrative(
        cagr_data, foreign_funding_isnull, exp_type, num_years=updated_num_years, lang=lang
    )

    return fig, narrative


def create_func_growth_figure(df, exp_type, lang="en"):
    color_mapping = {
        func: FUNC_COLORS.get(func, "gray") for func in df["func"].unique()
    }
    overall_label = t("label.overall_budget", lang)
    color_mapping[overall_label] = "rgba(150, 150, 150, 0.8)"

    fig = go.Figure()
    for func, group in df.groupby("func"):
        group = group.sort_values("year")
        # The "overall_label" trace is already translated via t(); other
        # traces receive raw COFOG names that need translation for display.
        display_name = func if func == overall_label else translate_func(func, lang)
        fig.add_trace(
            go.Scatter(
                x=group["year"],
                y=group[f"yoy_{exp_type}"],
                mode="lines+markers",
                name=display_name,
                line=dict(
                    color=color_mapping.get(func, "gray"),
                    width=2,
                    dash="dot" if func == overall_label else "solid",
                ),
                legendgroup='primary' if func != overall_label else "secondary",
                marker=dict(size=4, opacity=0.8),
                hovertemplate=(
                    "<b>" + t("hover.func_category", lang) + ":</b> %{fullData.name}<br>"
                    "<b>" + t("hover.year", lang) + ":</b> %{x}<br>"
                    "<b>" + t("hover.growth_rate", lang) + ":</b> %{y:.1f}%<extra></extra>"
                ),
                connectgaps=False,
                visible="legendonly"
                if func not in DEFAULT_VISIBLE_CATEGORIES and func != overall_label
                else True,
            )
        )

    fig.update_layout(
        title=t("chart.budget_func_fluctuation", lang),
        yaxis_title=t("axis.yoy_growth_rate", lang),
        legend_title_text="",
        hovermode="closest",
        template="plotly_white",
        legend=dict(
            tracegroupgap=10
        ),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=-0.14,
                y=-0.2,
                text=t("source.boost_wb", lang),
                showarrow=False,
                font=dict(size=12),
            )
        ],
        xaxis=dict(
            tickmode="linear",
            tickformat=".0f",
            dtick=1,
        ),
    )

    return fig


def format_budget_increment_narrative(
    data, foreign_funding_isnull, exp_type, num_years, lang="en", threshold=0.75
):
    budget_cagr = data["Overall budget"]
    highest_func_cat_raw, highest_cagr = data["highest"]
    lowest_func_cat_raw, lowest_cagr = data["lowest"]
    # Two forms per category for the templates:
    #  - Bare label form ("Santé") for "Les catégories X et Y" apposition
    #  - Narrative form ("la santé") for mid-sentence prose like
    #    "avec la santé à 5.2 %"
    highest_func_cat = translate_func(highest_func_cat_raw, lang)
    lowest_func_cat = translate_func(lowest_func_cat_raw, lang)
    highest_func_cat_narrative = translate_func(highest_func_cat_raw, lang, narrative=True)
    lowest_func_cat_narrative = translate_func(lowest_func_cat_raw, lang, narrative=True)

    if budget_cagr < 0:
        budget_growth_phrase = t("narrative.budget_declined", lang, rate=abs(budget_cagr))
    else:
        budget_growth_phrase = t("narrative.budget_grown", lang, rate=budget_cagr)

    budget_growth_phrase += t("narrative.budget_cagr", lang)
    if exp_type == "real_domestic_funded_budget":
        budget_growth_phrase += t("narrative.budget_after_inflation", lang)
    else:
        budget_growth_phrase += t("narrative.budget_period_end", lang)

    if lowest_cagr < 0:
        lowest_phrase = t("narrative.declined_by_rate", lang, rate=abs(lowest_cagr))
    else:
        lowest_phrase = t("narrative.grew_modest", lang, rate=lowest_cagr)

    if highest_cagr > 10:
        highest_phrase = t("narrative.expanded_significantly", lang, rate=highest_cagr)
    else:
        highest_phrase = t("narrative.grew_steady", lang, rate=highest_cagr)

    if abs(highest_cagr - lowest_cagr) < threshold:
        func_comparison = t("narrative.both_similar_rates", lang,
                            high=highest_func_cat, low=lowest_func_cat,
                            high_narrative=highest_func_cat_narrative,
                            low_narrative=lowest_func_cat_narrative,
                            high_rate=highest_cagr, low_rate=lowest_cagr)
    elif highest_cagr > lowest_cagr:
        func_comparison = t("narrative.high_expanded", lang,
                            high=highest_func_cat, low=lowest_func_cat,
                            high_narrative=highest_func_cat_narrative,
                            low_narrative=lowest_func_cat_narrative,
                            high_phrase=highest_phrase, low_phrase=lowest_phrase)
    else:
        func_comparison = t("narrative.low_outpacing", lang,
                            high=highest_func_cat, low=lowest_func_cat,
                            high_narrative=highest_func_cat_narrative,
                            low_narrative=lowest_func_cat_narrative,
                            high_phrase=highest_phrase, low_phrase=lowest_phrase)

    if foreign_funding_isnull:
        external_financing_note = t("narrative.external_financing_included", lang)
    else:
        external_financing_note = t("narrative.external_financing_excluded", lang)

    return (
        (
            t("narrative.budget_growth", lang, num_years=num_years, growth_phrase=budget_growth_phrase)
            + f"{func_comparison} "
            + f"{external_financing_note}"
        ),
    )
