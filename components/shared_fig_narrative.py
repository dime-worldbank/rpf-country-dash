from dash import Output, Input, callback, html
import pandas as pd
import plotly.graph_objects as go

OP_WAGE_BILL = "Ops: Wage bill"
OP_GOOD_SERVICES = "Ops: Goods and Services"
CAPEX = "Capital expenditures"
OTHER = "Other Spending"

def prepare_prop_econ_by_func_df(func_econ_df, agg_dict):
    filtered_df = func_econ_df[func_econ_df["func"].isin(["Health", "Education"])]
    econ_mapping = {
        "Wage bill": OP_WAGE_BILL,
        "Goods and services": OP_GOOD_SERVICES,
        "Capital expenditures": CAPEX,
    }
    filtered_df = filtered_df.assign(
        econ=filtered_df["econ"].map(econ_mapping).fillna(OTHER)
    )
    prop_econ_by_func_df = (
        filtered_df
        .groupby(["country_name", "year", "func", "econ"], as_index=False)
        .agg(agg_dict)
        .assign(
            proportion=lambda df: (
                100
                * df["real_expenditure"]
                / df.groupby(["country_name", "year", "func"])[ "real_expenditure" ].transform("sum")
            )
        )
    )
    return prop_econ_by_func_df


def format_econ_narrative(data, country_name, category):
    data = data.sort_values("year")
    start_year, latest_year = data["year"].iloc[0], data["year"].iloc[-1]

    latest_data = data[data["year"] == latest_year].squeeze()
    start_data = data[data["year"] == start_year].squeeze()
    cap_spending_pct = latest_data[CAPEX]
    gs_spending_pct = latest_data[OP_GOOD_SERVICES]
    emp_comp_pct = latest_data[OP_WAGE_BILL]
    op_spenging_pct = gs_spending_pct + emp_comp_pct
    categories = [
        OTHER,
        OP_WAGE_BILL,
        OP_GOOD_SERVICES,
        CAPEX,
    ]
    stable_threshold = 5
    changes = {cat: latest_data[cat] - start_data[cat] for cat in categories}
    trends = {
        cat: (
            "remained stable"
            if abs(changes[cat]) < stable_threshold
            else "increased"
            if changes[cat] > 0
            else "decreased"
        )
        for cat in categories
    }
    operational_resources = {
        "Education": "school materials",
        "Health": "healthcare supplies",
    }
    capital_investment_targets = {
        "Education": "new schools",
        "Health": "new healthcare facilities",
    }
    essential_resources = {
        "Education": "essential teaching materials and classroom resources",
        "Health": "medical supplies and patient care resources",
    }
    support_materials = {
        "Education": "learning materials",
        "Health": "treatment support materials",
    }
    employee_compensation_narrative = (
        f" This indicates that a significant portion of spending is directed towards salaries and benefits, leaving limited room for non-salary operational costs such as {operational_resources[category]} and facility maintenance."
        if latest_data[OP_WAGE_BILL] > 70
        else " This indicates a balanced allocation between salaries and other operational resources to support service delivery, potentially enabling enhanced investment in resources and services that directly impact service delivery."
    )

    capital_spending_narrative = (
        f"Meanwhile, capital spending represented {cap_spending_pct:.0f}% of total {category} spending in {latest_year}, "
        + (
            "indicating potential under-investment in long-term infrastructure, which could affect future service delivery."
            if cap_spending_pct < 10
            else "which is within the expected range for social sectors but may require further prioritization based on infrastructure needs."
            if 10 <= cap_spending_pct <= 25
            else "suggesting a strong emphasis on infrastructure and capacity expansion."
        )
    )

    capital_spending_change_narrative = (
        f"Capital spending has {trends[CAPEX]}"
        + (
            "."
            if trends[CAPEX] == "remained stable"
            else f" by {abs(changes[CAPEX]):.0f}%, "
            + (
                f"reflecting reduced investment in {capital_investment_targets[category]} and infrastructure."
                if changes[CAPEX] < 0
                else f"suggesting a stronger commitment to expanding and upgrading {category} facilities."
            )
        )
    )
    emp_comp_spending_change_narrative = (
        f"Employee compensation has {trends[OP_WAGE_BILL]}"
        + (
            "."
            if trends[OP_WAGE_BILL] == "remained stable"
            else f" by {abs(changes[OP_WAGE_BILL]):.0f}%, "
            + (
                "possibly driven by wage increases and workforce expansion."
                if changes[OP_WAGE_BILL] > stable_threshold
                else "remaining stable relative to overall spending trends."
            )
        )
    )
    gs_spending_change_narrative = (
        f"Goods and services spending has {trends[OP_GOOD_SERVICES]}"
        + (
            "."
            if trends[OP_GOOD_SERVICES] == "remained stable"
            else f" by {abs(changes[OP_GOOD_SERVICES]):.0f}%, "
            + (
                f"potentially affecting the availability of {essential_resources[category]}."
                if changes[OP_GOOD_SERVICES] < 0
                else f"allowing for enhanced support for {support_materials[category]} and maintenance needs."
            )
        )
    )

    return html.Div(
        [
            html.P(
                f"In {country_name}, operational spending accounted for {op_spenging_pct:.0f}% of total {category.lower()} spending in {latest_year}, "
                f"with {emp_comp_pct:.0f}% allocated to employee compensation and {gs_spending_pct:.0f}% to goods and services."
                f"{employee_compensation_narrative}"
            ),
            html.P(f"{capital_spending_narrative}"),
            html.P(
                f"Between {start_year} and {latest_year}, the earliest and latest year for which data is available, spending patterns are as follows:"
            ),
            html.Ul(
                [
                    html.Li(f"{capital_spending_change_narrative}"),
                    html.Li(f"{emp_comp_spending_change_narrative}"),
                    html.Li(f"{gs_spending_change_narrative}"),
                ]
            ),
        ]
    )


def generate_econ_figure(data, category):
    fig = go.Figure()
    for econ_category in data.columns[1:]:
        fig.add_trace(
            go.Scatter(
                x=data["year"],
                y=data[econ_category],
                mode="lines",
                line=dict(width=0.5),
                stackgroup="one",
                name=econ_category,
            )
        )
    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(
        fixedrange=True,
        showticklabels=True,
        tickmode="array",
        tickvals=[20, 40, 60, 80, 100],
    )
    fig.update_layout(
        barmode="stack",
        hovermode="x unified",
        title=f"How have expenditure priorities changed?",
        plot_bgcolor="white",
        yaxis_title=f"Percentage of total {category.lower()} expenditure",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=20, r=20, t=50, b=80),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.13,
                xanchor="left",
                text="Source: BOOST Database, World Bank",
                showarrow=False,
                font=dict(size=12, color="grey"),
            ),
        ],
    )
    fig.update_traces(
            hovertemplate="%{y:.2f}%"
    )
    return fig


@callback(
    [
        Output("econ-breakdown-func", "figure"),
        Output("econ-breakdown-func-narrative", "children"),
        Input("stored-data-func-econ", "data"),
        Input("country-select", "value"),
        Input("page-selector", "data"),
    ],
)
def render_econ_breakdown(data, country_name, page_category):
    df = pd.DataFrame(data["econ_expenditure_prop_by_func_country_year"])
    filtered_df = df[
        (df["country_name"] == country_name) & (df["func"] == page_category)
    ]
    pivot_df = filtered_df.pivot_table(
        index="year", columns="econ", values="proportion", aggfunc="sum", fill_value=0
    ).reset_index()

    fig = generate_econ_figure(pivot_df, page_category)
    narrative = format_econ_narrative(pivot_df, country_name, page_category)

    return fig, narrative
