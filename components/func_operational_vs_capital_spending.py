from dash import html
import pandas as pd
import plotly.graph_objects as go
from translations import t, genitive, locative
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

    # Localized lowercase sector label for mid-sentence use
    func_label = t(f"sector.{func.lower()}", lang)

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

    def _direction(delta):
        if abs(delta) < stable_threshold:
            return "stable"
        return "up" if delta > 0 else "down"

    directions = {cat: _direction(changes[cat]) for cat in categories}

    resources = t(f"econ.operational_resources.{func}", lang)
    targets = t(f"econ.capital_targets.{func}", lang)
    essential = t(f"econ.essential_resources.{func}", lang)
    materials = t(f"econ.support_materials.{func}", lang)
    facilities = t(f"sector.{func.lower()}.facilities", lang)

    if latest_data[OP_WAGE_BILL] > 70:
        emp_narrative = t("narrative.emp_comp_high", lang, resources=resources)
    else:
        emp_narrative = t("narrative.emp_comp_balanced", lang)

    func_gen = genitive(lang, func_label)
    country_display = t(f"country.{country_name}", lang)
    intro_text = t("narrative.econ_breakdown_intro", lang,
                    country=country_display,
                    country_loc=locative(lang, country_display),
                    emp_pct=emp_comp_pct,
                    func=func_label, func_gen=func_gen, other_pct=other_pct,
                    year=latest_year, emp_narrative=emp_narrative)

    capital_base = t("narrative.capital_spending", lang,
                     pct=cap_spending_pct, func=func_label, func_gen=func_gen,
                     year=latest_year)
    if cap_spending_pct < 10:
        capital_text = capital_base + t("narrative.capital_under_investment", lang)
    elif 10 <= cap_spending_pct <= 25:
        capital_text = capital_base + t("narrative.capital_expected_range", lang)
    else:
        capital_text = capital_base + t("narrative.capital_strong_emphasis", lang)

    patterns_intro = t("narrative.spending_patterns_intro", lang, start_year=start_year, end_year=latest_year)

    # Capital spending change
    if directions[CAPEX] == "stable":
        cap_change_text = t("narrative.capital_spending_change_stable", lang)
    else:
        key = "narrative.capital_spending_change_up" if directions[CAPEX] == "up" else "narrative.capital_spending_change_down"
        cap_change_text = t(key, lang, amount=abs(changes[CAPEX]), facilities=facilities, targets=targets)

    # Employee compensation change
    if directions[OP_WAGE_BILL] == "stable":
        emp_change_text = t("narrative.emp_comp_change_stable", lang)
    else:
        key = "narrative.emp_comp_change_up" if directions[OP_WAGE_BILL] == "up" else "narrative.emp_comp_change_down"
        emp_change_text = t(key, lang, amount=abs(changes[OP_WAGE_BILL]))

    # Other spending change
    if directions[OTHER] == "stable":
        other_change_text = t("narrative.other_spending_change_stable", lang)
    else:
        key = "narrative.other_spending_change_up" if directions[OTHER] == "up" else "narrative.other_spending_change_down"
        other_change_text = t(key, lang, amount=abs(changes[OTHER]), resources=essential, materials=materials)

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
    func_label = t(f"sector.{func.lower()}", lang)
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
        yaxis_title=t("axis.pct_total_func_expenditure", lang, func=func_label),
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
