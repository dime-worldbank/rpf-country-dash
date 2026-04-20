import numpy as np
import pandas as pd
import plotly.graph_objects as go
from constants import FUNC_COLORS
import server_store
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


def render_fig_and_narrative(data, country, exp_type):
    if not data or not country:
        return empty_plot("Loading..."), "Loading..."
    country_budget_changes_df = server_store.get("func_by_country_year")
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
    overall_budget_df["func"] = "Overall budget"

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
    updated_start_year = country_budget_changes_df.loc[
        (country_budget_changes_df["func"] == "Overall budget")
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
            empty_plot("Inflation-adjusted budget data unavailable"),
            generate_error_prompt(
                "DATA_UNAVAILABLE_DATASET_NAME",
                dataset_name="Inflation adjusted domestic funded budget",
            ),
        )
    fig = create_func_growth_figure(country_budget_changes_df, exp_type)

    highest_func_cat = max(
        (k for k in valid_cagr_dict if k != "Overall budget"), key=valid_cagr_dict.get
    )
    other_candidates = [
        k for k in valid_cagr_dict if k != "Overall budget" and k != highest_func_cat
    ]

    if other_candidates:
        lowest_func_cat = min(other_candidates, key=valid_cagr_dict.get)
    else:
        lowest_func_cat = highest_func_cat

    cagr_data = {
        "Overall budget": func_cagr_dict["Overall budget"],
        "highest": (highest_func_cat, func_cagr_dict[highest_func_cat]),
        "lowest": (lowest_func_cat, func_cagr_dict[lowest_func_cat]),
    }
    narrative = format_budget_increment_narrative(
        cagr_data, foreign_funding_isnull, exp_type, num_years=updated_num_years
    )

    return fig, narrative


def create_func_growth_figure(df, exp_type):
    color_mapping = {
        func: FUNC_COLORS.get(func, "gray") for func in df["func"].unique()
    }
    color_mapping["Overall budget"] = "rgba(150, 150, 150, 0.8)"

    fig = go.Figure()
    for func, group in df.groupby("func"):
        group = group.sort_values("year")
        fig.add_trace(
            go.Scatter(
                x=group["year"],
                y=group[f"yoy_{exp_type}"],
                mode="lines+markers",
                name=func,
                line=dict(
                    color=color_mapping.get(func, "gray"),
                    width=2,
                    dash="dot" if func == "Overall budget" else "solid",
                ),
                legendgroup='primary' if func != "Overall budget" else "secondary",
                marker=dict(size=4, opacity=0.8),
                hovertemplate=(
                    "<b>Functional Category:</b> %{fullData.name}<br>"
                    "<b>Year:</b> %{x}<br>"
                    "<b>Growth Rate:</b> %{y:.1f}%<extra></extra>"
                ),
                connectgaps=False,
                visible="legendonly"
                if func not in DEFAULT_VISIBLE_CATEGORIES
                else True,
            )
        )

    fig.update_layout(
        title="How do budgets for functional categories fluctuate over time?",
        yaxis_title="Year-on-year growth rate (%)",
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
                text="Source: BOOST, World Bank",
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
    data, foreign_funding_isnull, exp_type, num_years, threshold=0.75
):
    budget_cagr = data["Overall budget"]
    highest_func_cat, highest_cagr = data["highest"]
    lowest_func_cat, lowest_cagr = data["lowest"]

    if budget_cagr < 0:
        budget_growth_phrase = f"declined at an average rate of {abs(budget_cagr):.1f}% per year"
    else:
        budget_growth_phrase = f"grown at an average rate of {budget_cagr:.1f}% per year"

    budget_growth_phrase += ', calculated using the compound annual growth rate (CAGR)'
    if exp_type == "real_domestic_funded_budget":
        budget_growth_phrase += ' after accounting for inflation. '
    else:
        budget_growth_phrase += '. '

    if lowest_cagr < 0:
        lowest_phrase = f"declined by {abs(lowest_cagr):.1f}%"
    else:
        lowest_phrase = f"grew at a modest rate of {lowest_cagr:.1f}%"

    if highest_cagr > 10:
        highest_phrase = f"expanded significantly at {highest_cagr:.1f}%"
    else:
        highest_phrase = f"grew at a steady rate of {highest_cagr:.1f}%"

    if abs(highest_cagr - lowest_cagr) < threshold:
        func_comparison = (
            f"Both the {highest_func_cat} and {lowest_func_cat} categories have grown at similar rates, "
            f"with {highest_func_cat} growing at {highest_cagr:.1f}% and {lowest_func_cat} at {lowest_cagr:.1f}% per year."
        )
    elif highest_cagr > lowest_cagr:
        func_comparison = (
            f"The {highest_func_cat} category {highest_phrase}, "
            f"while the {lowest_func_cat} category {lowest_phrase}. "
            f"This might suggest a policy shift towards prioritizing the {highest_func_cat} category, if resource deployment is in line with public policy priorities."
        )
    else:
        func_comparison = (
            f"The {lowest_func_cat} category {lowest_phrase}, "
            f"outpacing the {highest_func_cat} category, which {highest_phrase}. "
            f"This suggests a greater focus on the {highest_func_cat} category, if resource deployment is in line with public policy priorities."
        )

    if foreign_funding_isnull:
        external_financing_note = (
            "This analysis currently includes external financing as the budget data used has limited granularity. "
            "It would ideally exclude external financing due to its volatility."
        )
    else:
        external_financing_note = (
            "This analysis excludes external financing as it tends to be volatile."
        )

    return (
        (
            f"Over the past {num_years} years, the national budget has {budget_growth_phrase}"
            f"{func_comparison} "
            f"{external_financing_note}"
        ),
    )
