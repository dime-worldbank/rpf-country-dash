import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import traceback
from queries import QueryService
from wwbi_data import WWBIDataService
from utils import (
    empty_plot,
    filter_country_sort_year,
    generate_error_prompt,
    millify,
    require_login,
)

db = QueryService.get_instance()
wwbi = WWBIDataService.get_instance()

dash.register_page(__name__)


@require_login
def layout():
    return html.Div(
        children=[
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Tabs(
                            id="jobs-tabs",
                            active_tab="jobs-tab-time",
                            children=[
                                dbc.Tab(label="Over Time", tab_id="jobs-tab-time"),
                            ],
                            style={"marginBottom": "2rem"},
                        ),
                        html.Div(id="jobs-content"),
                    ]
                ),
            ),
            dcc.Store(id="stored-data-jobs-employment"),
            dcc.Store(id="stored-data-jobs-wage-premium"),
            dcc.Store(id="stored-data-jobs-composition"),
            dcc.Store(id="stored-data-jobs-gender"),
        ]
    )


@callback(
    Output("stored-data-jobs-employment", "data"),
    Input("stored-data-jobs-employment", "data"),
    Input("stored-data", "data"),
)
def fetch_jobs_employment_data_once(jobs_data, shared_data):
    if jobs_data is None and shared_data is not None:
        countries = shared_data.get("countries", [])
        employment_data = wwbi.get_public_private_employment(country_whitelist=countries)

        return {
            "employment": employment_data.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("stored-data-jobs-wage-premium", "data"),
    Input("stored-data-jobs-wage-premium", "data"),
    Input("stored-data", "data"),
)
def fetch_jobs_wage_data_once(jobs_data, shared_data):
    if jobs_data is None and shared_data is not None:
        countries = shared_data.get("countries", [])
        wage_data = wwbi.get_wage_premium_data(country_whitelist=countries)

        return {
            "wage_premium": wage_data.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("stored-data-jobs-composition", "data"),
    Input("stored-data-jobs-composition", "data"),
    Input("stored-data", "data"),
)
def fetch_jobs_composition_data_once(jobs_data, shared_data):
    if jobs_data is None and shared_data is not None:
        countries = shared_data.get("countries", [])
        composition_data = wwbi.get_employment_composition(country_whitelist=countries)

        return {
            "composition": composition_data.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("stored-data-jobs-gender", "data"),
    Input("stored-data-jobs-gender", "data"),
    Input("stored-data", "data"),
)
def fetch_jobs_gender_data_once(jobs_data, shared_data):
    if jobs_data is None and shared_data is not None:
        countries = shared_data.get("countries", [])
        gender_data = wwbi.get_gender_employment_data(country_whitelist=countries)

        return {
            "gender": gender_data.to_dict("records"),
        }
    return dash.no_update


@callback(
    Output("jobs-content", "children"),
    Input("jobs-tabs", "active_tab"),
)
def render_jobs_content(tab):
    if tab == "jobs-tab-time":
        return html.Div(
            [
                # Section 1: Public vs Private Employment
                dbc.Row(
                    dbc.Col(
                        html.H3(
                            children="Who Employs the Workforce?",
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="jobs-public-private-narrative",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="jobs-public-private",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 12, "offset": 0},
                        ),
                    ]
                ),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                # Section 2: Wage Premium
                dbc.Row(
                    dbc.Col(
                        html.H3(
                            children="Is Public Sector Work Better Paid?",
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="jobs-wage-premium-narrative",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="jobs-wage-premium",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 12, "offset": 0},
                        ),
                    ]
                ),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                # Section 3: Employment Composition & Wage Bill
                dbc.Row(
                    dbc.Col(
                        html.H3(
                            children="Where Are Public Workers Employed and What Does Government Spend on Wages?",
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="jobs-composition-narrative",
                                children="loading...",
                            ),
                            html.P(
                                id="jobs-wage-bill-narrative",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="jobs-composition",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                        dbc.Col(
                            dcc.Graph(
                                id="jobs-wage-bill",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 6, "offset": 0},
                        ),
                    ]
                ),
                dbc.Row(
                    dbc.Col(
                        html.Hr(),
                    )
                ),
                # Section 4: Gender Dimensions
                dbc.Row(
                    dbc.Col(
                        html.H3(
                            children="How Are Women Represented in Public Jobs?",
                        )
                    )
                ),
                dbc.Row(
                    dbc.Col(
                        [
                            html.P(
                                id="jobs-gender-narrative",
                                children="loading...",
                            ),
                        ]
                    )
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="jobs-gender",
                                config={"displayModeBar": False},
                            ),
                            xs={"size": 12, "offset": 0},
                            sm={"size": 12, "offset": 0},
                            md={"size": 12, "offset": 0},
                            lg={"size": 12, "offset": 0},
                        ),
                    ]
                ),
            ]
        )


# Section 1: Public vs Private Employment
def public_private_narrative(df, country):
    try:
        df = df.sort_values('year')
        latest_year = df['year'].max()
        earliest_year = df['year'].min()

        latest = df[df['year'] == latest_year].iloc[0]
        earliest = df[df['year'] == earliest_year].iloc[0]

        public_share_latest = latest['BI.EMP.PWRK.PB.ZS'] * 100
        public_share_earliest = earliest['BI.EMP.PWRK.PB.ZS'] * 100
        trend = "increased" if public_share_latest > public_share_earliest else "decreased"
        ratio = (100 - public_share_latest) / public_share_latest

        text = f"In {country}, the public sector accounts for {public_share_latest:.1f}% of total salaried employment as of {int(latest_year)}, meaning approximately 1 in {int(100/public_share_latest)} salaried employed workers work for the government. "

        if earliest_year != latest_year:
            text += f"Between {int(earliest_year)} and {int(latest_year)}, the public sector's share has {trend} from {public_share_earliest:.1f}% to {public_share_latest:.1f}%. "

        text += f"For every worker employed in the public sector, there were approximately {ratio:.0f} workers in the private salaried sector. "

        if pd.notna(latest.get('BI.EMP.PWRK.PB.FE.ZS')):
            female_public = latest['BI.EMP.PWRK.PB.FE.ZS'] * 100
            gap = female_public - public_share_latest
            if gap > 0:
                text += f"{female_public:.1f}% of female workers are employed in the public sector while the public sector accounts for only {public_share_latest:.1f}% of total salaried employment, a {gap:.1f} percentage point difference suggesting that public sector jobs are more accessible to women."
            elif gap < 0:
                text += f"{female_public:.1f}% of female workers are employed in the public sector while the public sector accounts for {public_share_latest:.1f}% of total salaried employment, a {abs(gap):.1f} percentage point gap suggesting that public sector jobs are less accessible to women."
            else:
                text += f"{female_public:.1f}% of female workers are employed in the public sector, matching the public sector's {public_share_latest:.1f}% share of total salaried employment."

        return text
    except Exception as e:
        traceback.print_exc()
        return generate_error_prompt("DATA_UNAVAILABLE")


@callback(
    Output("jobs-public-private", "figure"),
    Output("jobs-public-private-narrative", "children"),
    Input("stored-data-jobs-employment", "data"),
    Input("country-select", "value"),
)
def render_public_private(data, country):
    if not data:
        return empty_plot("Loading..."), "Loading..."

    df = pd.DataFrame(data["employment"])
    df = filter_country_sort_year(df, country)

    if df.empty or 'BI.EMP.PWRK.PB.ZS' not in df.columns:
        return (
            empty_plot("No data available for this country"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    df = df.dropna(subset=['BI.EMP.PWRK.PB.ZS'])

    if df.empty:
        return (
            empty_plot("No data available for this country"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    fig = go.Figure()

    df['public_share_pct'] = df['BI.EMP.PWRK.PB.ZS'] * 100
    df['private_share_pct'] = 100 - df['public_share_pct']

    fig.add_trace(
        go.Bar(
            name="Public Sector",
            x=df['year'],
            y=df['public_share_pct'],
            marker_color="darkblue",
            text=df['public_share_pct'],
            texttemplate='%{text:.1f}%',
            textposition='inside',
        )
    )

    fig.add_trace(
        go.Bar(
            name="Private Sector",
            x=df['year'],
            y=df['private_share_pct'],
            marker_color="rgb(160, 209, 255)",
            text=df['private_share_pct'],
            texttemplate='%{text:.1f}%',
            textposition='inside',
        )
    )

    fig.update_layout(
        barmode="stack",
        plot_bgcolor="white",
        title="What % of salaried jobs are public vs private sector?",
        yaxis_title="Percentage of salaried employment",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.15,
                text="Source: Worldwide Bureaucracy Indicators (WWBI), World Bank",
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)

    narrative = public_private_narrative(df, country)
    return fig, narrative


# Section 2: Wage Premium
def wage_premium_narrative(df, country):
    try:
        df = df.sort_values('year')
        latest_year = df['year'].max()
        earliest_year = df['year'].min()

        df_with_overall = df.dropna(subset=['BI.WAG.PREM.PB'])

        if df_with_overall.empty:
            return "Wage premium data is not available for this country."

        latest = df_with_overall[df_with_overall['year'] == df_with_overall['year'].max()].iloc[0]
        earliest = df_with_overall[df_with_overall['year'] == df_with_overall['year'].min()].iloc[0]

        premium_latest = latest['BI.WAG.PREM.PB']
        premium_earliest = earliest['BI.WAG.PREM.PB']

        trend = "increased" if premium_latest > premium_earliest else "decreased"

        text = f"Public sector workers in {country} earn, on average, {premium_latest:.1f}% more than comparable private sector workers as of {int(latest['year'])}. "

        if int(earliest['year']) != int(latest['year']):
            text += f"This premium has {trend} from {premium_earliest:.1f}% in {int(earliest['year'])}, suggesting that public sector wages have grown {'faster' if premium_latest > premium_earliest else 'slower'} than private sector wages. "

        if pd.notna(latest.get('BI.WAG.PREM.ED.GP')) or pd.notna(latest.get('BI.WAG.PREM.HE.GP')):
            text += "The premium varies across sectors: "
            premiums = []
            if pd.notna(latest.get('BI.WAG.PREM.ED.GP')):
                premiums.append(f"education workers enjoy a premium of {latest['BI.WAG.PREM.ED.GP']:.1f}%")
            if pd.notna(latest.get('BI.WAG.PREM.HE.GP')):
                premiums.append(f"health workers see {latest['BI.WAG.PREM.HE.GP']:.1f}%")
            text += " while ".join(premiums) + ". "

        if pd.notna(latest.get('BI.WAG.PREM.PB.FE')):
            female_premium = latest['BI.WAG.PREM.PB.FE']
            text += f"Female workers in the public sector experience a wage premium of {female_premium:.1f}% compared to private sector female workers, suggesting that public sector employment provides relatively better compensation for women."

        return text
    except Exception as e:
        traceback.print_exc()
        return generate_error_prompt("DATA_UNAVAILABLE")


@callback(
    Output("jobs-wage-premium", "figure"),
    Output("jobs-wage-premium-narrative", "children"),
    Input("stored-data-jobs-wage-premium", "data"),
    Input("country-select", "value"),
)
def render_wage_premium(data, country):
    if not data:
        return empty_plot("Loading..."), "Loading..."

    df = pd.DataFrame(data["wage_premium"])
    df = filter_country_sort_year(df, country)

    if df.empty:
        return (
            empty_plot("No data available for this country"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    df = df.dropna(subset=['BI.WAG.PREM.PB'], how='all')

    if df.empty:
        return (
            empty_plot("No wage premium data available for this country"),
            "Wage premium data is not available for this country.",
        )

    fig = go.Figure()

    if 'BI.WAG.PREM.PB' in df.columns and df['BI.WAG.PREM.PB'].notna().any():
        fig.add_trace(
            go.Scatter(
                name="Overall Premium",
                x=df['year'],
                y=df['BI.WAG.PREM.PB'],
                mode="lines+markers",
                line=dict(color="darkblue", width=3),
            )
        )

    if 'BI.WAG.PREM.PB.FE' in df.columns and df['BI.WAG.PREM.PB.FE'].notna().any():
        fig.add_trace(
            go.Scatter(
                name="Female Premium",
                x=df['year'],
                y=df['BI.WAG.PREM.PB.FE'],
                mode="lines+markers",
                line=dict(color="deeppink", dash="dot"),
            )
        )

    if 'BI.WAG.PREM.ED.GP' in df.columns and df['BI.WAG.PREM.ED.GP'].notna().any():
        fig.add_trace(
            go.Scatter(
                name="Education Sector",
                x=df['year'],
                y=df['BI.WAG.PREM.ED.GP'],
                mode="lines+markers",
                line=dict(color="green", dash="dash"),
            )
        )

    if 'BI.WAG.PREM.HE.GP' in df.columns and df['BI.WAG.PREM.HE.GP'].notna().any():
        fig.add_trace(
            go.Scatter(
                name="Health Sector",
                x=df['year'],
                y=df['BI.WAG.PREM.HE.GP'],
                mode="lines+markers",
                line=dict(color="red", dash="dash"),
            )
        )

    fig.update_layout(
        plot_bgcolor="white",
        title="How much more do public sector workers earn?",
        yaxis_title="Wage premium (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.15,
                text="Source: Worldwide Bureaucracy Indicators (WWBI), World Bank",
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)

    narrative = wage_premium_narrative(df, country)
    return fig, narrative


# Section 3: Employment Composition & Wage Bill
def composition_narrative(comp_df, wage_df, country):
    try:
        comp_df = comp_df.sort_values('year')
        latest_year = comp_df['year'].max()
        earliest_year = comp_df['year'].min()

        latest_comp = comp_df[comp_df['year'] == latest_year].iloc[0]
        earliest_comp = comp_df[comp_df['year'] == earliest_year].iloc[0]

        sectors = []
        if pd.notna(latest_comp.get('BI.EMP.PWRK.ED.PB.ZS')):
            sectors.append(('education', latest_comp['BI.EMP.PWRK.ED.PB.ZS'] * 100, earliest_comp.get('BI.EMP.PWRK.ED.PB.ZS') * 100 if pd.notna(earliest_comp.get('BI.EMP.PWRK.ED.PB.ZS')) else None))
        if pd.notna(latest_comp.get('BI.EMP.PWRK.CA.PB.ZS')):
            sectors.append(('core public administration', latest_comp['BI.EMP.PWRK.CA.PB.ZS'] * 100, earliest_comp.get('BI.EMP.PWRK.CA.PB.ZS') * 100 if pd.notna(earliest_comp.get('BI.EMP.PWRK.CA.PB.ZS')) else None))
        if pd.notna(latest_comp.get('BI.EMP.PWRK.HE.PB.ZS')):
            sectors.append(('health', latest_comp['BI.EMP.PWRK.HE.PB.ZS'] * 100, earliest_comp.get('BI.EMP.PWRK.HE.PB.ZS') * 100 if pd.notna(earliest_comp.get('BI.EMP.PWRK.HE.PB.ZS')) else None))

        sectors.sort(key=lambda x: x[1], reverse=True)

        text = f"The public sector workforce in {country} is concentrated in "
        if len(sectors) >= 3:
            text += f"three key areas: {sectors[0][0]} ({sectors[0][1]:.0f}% of public employees), {sectors[1][0]} ({sectors[1][1]:.0f}%), and {sectors[2][0]} ({sectors[2][1]:.0f}%). "
        elif len(sectors) == 2:
            text += f"two key areas: {sectors[0][0]} ({sectors[0][1]:.0f}% of public employees) and {sectors[1][0]} ({sectors[1][1]:.0f}%). "

        if int(earliest_year) != int(latest_year) and len(sectors) > 0:
            changes = []
            for sector_name, latest_val, earliest_val in sectors[:2]:
                if pd.notna(earliest_val):
                    change = latest_val - earliest_val
                    trend = "increased" if change > 0 else "decreased"
                    changes.append(f"{sector_name}'s share {trend} from {earliest_val:.0f}% to {latest_val:.0f}%")

            if changes:
                text += f"Between {int(earliest_year)} and {int(latest_year)}, " + ", while ".join(changes) + "."

        return text
    except Exception as e:
        traceback.print_exc()
        return generate_error_prompt("DATA_UNAVAILABLE")


def wage_bill_narrative(wage_df, country):
    try:
        wage_df = wage_df.sort_values('year')
        latest_year = wage_df['year'].max()

        top_funcs = wage_df[wage_df['year'] == latest_year].nlargest(3, 'real_expenditure')

        if top_funcs.empty:
            return "Wage bill data is not available for this country."

        total_wage_bill = wage_df[wage_df['year'] == latest_year]['real_expenditure'].sum()

        text = f"Government wage bill spending in {int(latest_year)} was concentrated in "
        func_texts = []
        for idx, row in top_funcs.iterrows():
            share = (row['real_expenditure'] / total_wage_bill) * 100
            func_texts.append(f"{row['func']} ({share:.0f}% of total wage bill, {millify(row['real_expenditure'])})")

        text += ", ".join(func_texts) + "."

        return text
    except Exception as e:
        traceback.print_exc()
        return ""


@callback(
    Output("jobs-composition", "figure"),
    Output("jobs-composition-narrative", "children"),
    Input("stored-data-jobs-composition", "data"),
    Input("country-select", "value"),
)
def render_composition(data, country):
    if not data:
        return empty_plot("Loading..."), "Loading..."

    df = pd.DataFrame(data["composition"])
    df = filter_country_sort_year(df, country)

    if df.empty:
        return (
            empty_plot("No data available for this country"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    fig = go.Figure()

    sector_map = {
        'BI.EMP.PWRK.ED.PB.ZS': ('Education', 'rgb(17, 141, 255)'),
        'BI.EMP.PWRK.HE.PB.ZS': ('Health', 'rgb(255, 0, 102)'),
        'BI.EMP.PWRK.CA.PB.ZS': ('Core Admin', 'rgb(0, 176, 80)'),
        'BI.EMP.PWRK.PS.PB.ZS': ('Public Safety', 'rgb(255, 153, 0)'),
        'BI.EMP.PWRK.SS.PB.ZS': ('Social Security', 'rgb(153, 102, 255)'),
    }

    for col, (name, color) in sector_map.items():
        if col in df.columns and df[col].notna().any():
            fig.add_trace(
                go.Scatter(
                    name=name,
                    x=df['year'],
                    y=df[col] * 100,
                    mode='lines',
                    stackgroup='one',
                    line=dict(width=0.5, color=color),
                    fillcolor=color,
                )
            )

    fig.update_layout(
        plot_bgcolor="white",
        title="How is public employment distributed across sectors?",
        yaxis_title="Percentage of public employees",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.15,
                text="Source: Worldwide Bureaucracy Indicators (WWBI), World Bank",
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True, ticksuffix="%")

    narrative = composition_narrative(df, None, country)
    return fig, narrative


@callback(
    Output("jobs-wage-bill", "figure"),
    Output("jobs-wage-bill-narrative", "children"),
    Input("stored-data-func-econ", "data"),
    Input("country-select", "value"),
)
def render_wage_bill(data, country):
    if not data:
        return empty_plot("Loading..."), "Loading..."

    func_econ_df = pd.DataFrame(data["expenditure_by_country_func_econ_year"])

    wage_df = func_econ_df[(func_econ_df['econ'] == 'Wage bill') & (func_econ_df['country_name'] == country)]

    if wage_df.empty:
        return (
            empty_plot("No wage bill data available for this country"),
            "Wage bill data is not available for this country.",
        )

    wage_by_func = wage_df.groupby(['year', 'func']).agg({
        'real_expenditure': 'sum',
        'expenditure': 'sum'
    }).reset_index()

    wage_by_func = wage_by_func.sort_values(['year', 'real_expenditure'], ascending=[True, False])

    latest_year = wage_by_func['year'].max()
    top_funcs_latest = wage_by_func[wage_by_func['year'] == latest_year].nlargest(5, 'real_expenditure')['func'].tolist()

    wage_by_func_filtered = wage_by_func[wage_by_func['func'].isin(top_funcs_latest)]

    fig = go.Figure()

    for func in top_funcs_latest:
        func_data = wage_by_func_filtered[wage_by_func_filtered['func'] == func]
        fig.add_trace(
            go.Bar(
                name=func,
                x=func_data['year'],
                y=func_data['real_expenditure'],
            )
        )

    fig.update_layout(
        barmode='stack',
        plot_bgcolor="white",
        title="Which functions consume the most wage spending?",
        yaxis_title="Real wage bill expenditure (inflation-adjusted)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.15,
                text="Source: BOOST Database, World Bank",
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(fixedrange=True)

    narrative = wage_bill_narrative(wage_by_func, country)
    return fig, narrative


# Section 4: Gender Dimensions
def gender_narrative(df, country):
    try:
        df = df.sort_values('year')
        latest_year = df['year'].max()
        latest = df[df['year'] == latest_year].iloc[0]

        if pd.notna(latest.get('BI.EMP.PWRK.PB.FE.ZS')):
            overall_female = latest['BI.EMP.PWRK.PB.FE.ZS'] * 100
            text = f"Women comprise {overall_female:.1f}% of all public sector employment in {country} as of {int(latest_year)}. "
        else:
            return "Gender employment data is not available for this country."

        sectors = []
        if pd.notna(latest.get('BI.EMP.PUBS.FE.ED.ZS')):
            sectors.append(f"{latest['BI.EMP.PUBS.FE.ED.ZS']*100:.0f}% of education workers")
        if pd.notna(latest.get('BI.EMP.PUBS.FE.HE.ZS')):
            sectors.append(f"{latest['BI.EMP.PUBS.FE.HE.ZS']*100:.0f}% of health workers")

        if sectors:
            text += f"Gender representation varies across sectors: women represent {' and '.join(sectors)}. "

        if pd.notna(latest.get('BI.EMP.PUBS.FE.PN.ZS')) and pd.notna(latest.get('BI.EMP.PUBS.FE.SN.ZS')):
            prof_share = latest['BI.EMP.PUBS.FE.PN.ZS'] * 100
            mgr_share = latest['BI.EMP.PUBS.FE.SN.ZS'] * 100
            gap = prof_share - mgr_share
            text += f"While women hold {prof_share:.0f}% of professional positions in the public sector, they occupy only {mgr_share:.0f}% of managerial positions. This {gap:.0f} percentage point gap indicates a 'glass ceiling' effect."

        return text
    except Exception as e:
        traceback.print_exc()
        return generate_error_prompt("DATA_UNAVAILABLE")


@callback(
    Output("jobs-gender", "figure"),
    Output("jobs-gender-narrative", "children"),
    Input("stored-data-jobs-gender", "data"),
    Input("country-select", "value"),
)
def render_gender(data, country):
    if not data:
        return empty_plot("Loading..."), "Loading..."

    df = pd.DataFrame(data["gender"])
    df = filter_country_sort_year(df, country)

    if df.empty:
        return (
            empty_plot("No data available for this country"),
            generate_error_prompt("DATA_UNAVAILABLE"),
        )

    latest_year = df['year'].max()
    df_latest = df[df['year'] == latest_year].iloc[0]

    categories = []
    female_values = []

    category_map = {
        'BI.EMP.PWRK.PB.FE.ZS': 'Overall Public Sector',
        'BI.EMP.PUBS.FE.ED.ZS': 'Education',
        'BI.EMP.PUBS.FE.HE.ZS': 'Health',
        'BI.EMP.PUBS.FE.PN.ZS': 'Professionals',
        'BI.EMP.PUBS.FE.SN.ZS': 'Managers',
        'BI.EMP.PUBS.FE.CK.ZS': 'Clerks',
    }

    for col, label in category_map.items():
        if col in df_latest.index and pd.notna(df_latest[col]):
            categories.append(label)
            female_values.append(df_latest[col] * 100)

    if not categories:
        return (
            empty_plot("No gender data available for this country"),
            "Gender employment data is not available for this country.",
        )

    male_values = [100 - v for v in female_values]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name='Female',
            y=categories,
            x=female_values,
            orientation='h',
            marker_color='deeppink',
            text=[f"{v:.1f}%" for v in female_values],
            textposition='inside',
        )
    )

    fig.add_trace(
        go.Bar(
            name='Male',
            y=categories,
            x=male_values,
            orientation='h',
            marker_color='darkblue',
            text=[f"{v:.1f}%" for v in male_values],
            textposition='inside',
        )
    )

    fig.update_layout(
        barmode='stack',
        plot_bgcolor="white",
        title=f"How are women represented across public sector jobs? ({int(latest_year)})",
        xaxis_title="Percentage",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=0,
                y=-0.15,
                text="Source: Worldwide Bureaucracy Indicators (WWBI), World Bank",
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )

    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    narrative = gender_narrative(df, country)
    return fig, narrative
