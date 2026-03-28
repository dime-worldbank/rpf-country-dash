from dash import html
import pandas as pd
import plotly.graph_objects as go
from translations import t
from utils import empty_plot

OP_WAGE_BILL = "Wage bill"
CAPEX = "Capital expenditures"
OTHER = "Non-wage recurrent"

def prepare_prop_econ_by_func_df(func_econ_df, agg_dict):
    filtered_df = func_econ_df[func_econ_df["func"].isin(["Health", "Education"])]
    econ_mapping = {
        "Wage bill": OP_WAGE_BILL,
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


def _format_econ_narrative(data, country_name, func, lang="en"):
    data = data.sort_values("year")
    start_year, latest_year = data["year"].iloc[0], data["year"].iloc[-1]

    latest_data = data[data["year"] == latest_year].squeeze()
    start_data = data[data["year"] == start_year].squeeze()
    cap_spending_pct = latest_data[CAPEX]
    emp_comp_pct = latest_data[OP_WAGE_BILL]
    other_pct = 100 - cap_spending_pct - emp_comp_pct
    categories = [
        OTHER,
        OP_WAGE_BILL,
        CAPEX,
    ]
    stable_threshold = 5
    changes = {cat: latest_data[cat] - start_data[cat] for cat in categories}
    trends = {
        cat: (
            t("word.remained_stable", lang)
            if abs(changes[cat]) < stable_threshold
            else t("word.increased", lang)
            if changes[cat] > 0
            else t("word.decreased", lang)
        )
        for cat in categories
    }

    resources = t(f"econ.operational_resources.{func}", lang)
    targets = t(f"econ.capital_targets.{func}", lang)
    essential = t(f"econ.essential_resources.{func}", lang)
    materials = t(f"econ.support_materials.{func}", lang)

    if latest_data[OP_WAGE_BILL] > 70:
        emp_narrative = t("narrative.emp_comp_high", lang, resources=resources)
    else:
        emp_narrative = t("narrative.emp_comp_balanced", lang)

    intro_text = t("narrative.econ_breakdown_intro", lang,
                    country=country_name, emp_pct=emp_comp_pct,
                    func=func.lower(), other_pct=other_pct,
                    year=latest_year, emp_narrative=emp_narrative)

    capital_base = t("narrative.capital_spending", lang, pct=cap_spending_pct, func=func, year=latest_year)
    if cap_spending_pct < 10:
        capital_text = capital_base + t("narrative.capital_under_investment", lang)
    elif 10 <= cap_spending_pct <= 25:
        capital_text = capital_base + t("narrative.capital_expected_range", lang)
    else:
        capital_text = capital_base + t("narrative.capital_strong_emphasis", lang)

    patterns_intro = t("narrative.spending_patterns_intro", lang, start_year=start_year, end_year=latest_year)

    # Capital spending change
    cap_change = t("narrative.capital_spending_change", lang, trend=trends[CAPEX])
    remained_stable = t("word.remained_stable", lang)
    if trends[CAPEX] == remained_stable:
        cap_change_text = cap_change + "."
    else:
        cap_change_text = cap_change + t("narrative.by_amount", lang, amount=abs(changes[CAPEX]))
        if changes[CAPEX] < 0:
            cap_change_text += t("narrative.capital_reduced_investment", lang, targets=targets)
        else:
            cap_change_text += t("narrative.capital_stronger_commitment", lang, func=func)

    # Employee compensation change
    emp_change = t("narrative.emp_comp_change", lang, trend=trends[OP_WAGE_BILL])
    if trends[OP_WAGE_BILL] == remained_stable:
        emp_change_text = emp_change + "."
    else:
        emp_change_text = emp_change + t("narrative.by_amount", lang, amount=abs(changes[OP_WAGE_BILL]))
        if changes[OP_WAGE_BILL] > stable_threshold:
            emp_change_text += t("narrative.emp_comp_driven_by", lang)
        else:
            emp_change_text += t("narrative.emp_comp_stable_relative", lang)

    # Other spending change
    other_change = t("narrative.other_spending_change", lang, trend=trends[OTHER])
    if trends[OTHER] == remained_stable:
        other_change_text = other_change + "."
    else:
        other_change_text = other_change + t("narrative.by_amount", lang, amount=abs(changes[OTHER]))
        if changes[OTHER] < 0:
            other_change_text += t("narrative.other_affecting_availability", lang, resources=essential)
        else:
            other_change_text += t("narrative.other_enhanced_support", lang, materials=materials)

    return html.Div(
        [
            html.P(intro_text),
            html.P(capital_text),
            html.P(patterns_intro),
            html.Ul(
                [
                    html.Li(cap_change_text),
                    html.Li(emp_change_text),
                    html.Li(other_change_text),
                ]
            ),
        ]
    )


def _generate_econ_figure(data, func, lang="en"):
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
        title=t("chart.expenditure_priorities", lang),
        plot_bgcolor="white",
        yaxis_title=t("axis.pct_total_func_expenditure", lang, func=func.lower()),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=20, r=20, t=50, b=80),
    )
    fig.update_traces(
            hovertemplate="%{y:.2f}%"
    )
    return fig


def render_econ_breakdown(data, country_name, page_func, lang="en"):
    if not data:
        return empty_plot(t("loading", lang)), t("loading", lang)
    df = pd.DataFrame(data["econ_expenditure_prop_by_func_country_year"])
    filtered_df = df[
        (df["country_name"] == country_name) & (df["func"] == page_func)
    ]
    pivot_df = filtered_df.pivot_table(
        index="year", columns="econ", values="proportion", aggfunc="sum", fill_value=0
    ).reset_index()

    fig = _generate_econ_figure(pivot_df, page_func, lang=lang)
    narrative = _format_econ_narrative(pivot_df, country_name, page_func, lang=lang)

    return fig, narrative
