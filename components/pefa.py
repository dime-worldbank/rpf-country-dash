from collections import OrderedDict
from plotly.subplots import make_subplots
from utils import empty_plot
import numpy as np
import plotly.graph_objects as go
import re
import textwrap

SCORE_MAPPING = OrderedDict([
    (4, "A"),
    (3, "B"), (3.5, "B+"),
    (2, "C"), (2.5, "C+"),
    (1, "D"), (1.5, "D+"),
])

PILLAR_MAPPING = OrderedDict([
    ('pillar1_budget_reliability', '1. Budget reliability'),
    ('pillar2_transparency', '2. Transparency'),
    ('pillar3_asset_liability', '3. Asset and liability management'),
    ('pillar4_policy_based_budget', '4. Policy-based budgeting'),
    ('pillar5_predictability_and_control', '5. Predictability and control'),
    ('pillar6_accounting_and_reporting', '6. Accounting and reporting'),
    ('pillar7_external_audit', '7. External audit'),
])

PILLAR_NARRARIVE_MAPPING = OrderedDict([
    (
        'pillar1_budget_reliability',
        [
            'budget being realistic and implemented as intended',
            'aligning budget implementation with initial plans',
        ]
    ),
    (
        'pillar2_transparency',
        [
            'comprehensive, consistent, and accessible information on public financial management to the public',
            'providing comprehensive, consistent, and accessible information on public financial management to the public',
        ]
    ),
    (
        'pillar3_asset_liability',
        [
            'that public investments provide value for money, assets are recorded and managed, fiscal risks are identified, and debts and guarantees are prudently planned, approved, and monitored',
            'ensuring that public investments provide value for money, assets are recorded and managed, fiscal risks are identified, and debts and guarantees are prudently planned, approved, and monitored',
        ]
    ),
    (
        'pillar4_policy_based_budget',
        [
            'fiscal strategy and the budget being prepared with due regard to government fiscal policies, strategic plans, and adequate macroeconomic and fiscal projections',
            'ensuring fiscal strategy and the budget is prepared with due regard to government fiscal policies, strategic plans, and adequate macroeconomic and fiscal projections',
        ]
    ),
    (
        'pillar5_predictability_and_control',
        [
            'budget execution within a system of effective standards, processes, and internal controls, ensuring that resources are obtained and used as intended',
            'budget being implemented within a system of effective standards, processes, and internal controls, ensuring that resources are obtained and used as intended',
        ]
    ),
    (
        'pillar6_accounting_and_reporting',
        [
            'accurate and reliable records are maintained, and information is produced and disseminated at appropriate times to meet decision-making, management, and reporting needs',
            'maintaining accurate and reliable records, producing and disseminating information at appropriate times to meet decision-making, management, and reporting needs',
        ]
    ),
    (
        'pillar7_external_audit',
        [
            'public finances being independently reviewed and presence of external follow-up on the implementation of recommendations for improvement by the executive',
            'ensuring public finances is independently reviewed, and there is external follow-up on the implementation of recommendations for improvement by the executive',
        ]
    ),
])


def pefa_overall_figure(df, pov_df):
    title_text = "How did the overall quality of budget institutions change over time?"
    wrapped_title = "<br>".join(textwrap.wrap(title_text, width=45))
    if df.empty:
        return empty_plot("PEFA data not available", wrapped_title)

    pillar_columns = [col for col in df.columns if col.startswith('pillar')]
    overall_scores = df[pillar_columns].mean(axis=1)

    overall_grades = overall_scores.map(_score_to_grade)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # TODO: add a note to Details modal, explaining poverty rate threshold used is country income-level dependent
    fig.add_trace(
        go.Scatter(
            name="Poverty Rate",
            x=pov_df.year,
            y=pov_df.poverty_rate,
            mode="lines+markers",
            line=dict(color="darkred", shape="spline", dash="dot"),
            connectgaps=True,
            hovertemplate=("%{x}: %{y:.2f}%"),
        ),
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            name="PEFA Score",
            x=df.year,
            y=overall_scores,
            mode="lines+markers",
            marker_color="darkblue",
            hovertemplate=("%{x}: %{y:.2f} (%{customdata})"),
            customdata=overall_grades,
        ),
        secondary_y=False,
    )

    fig.update_xaxes(tickformat="d")
    fig.update_yaxes(
        title_text="Quality of Budget Institutions",
        secondary_y=False,
        tickvals=list(SCORE_MAPPING.keys()),
        ticktext=list(SCORE_MAPPING.values()),
        range=[0, 4.5],
    )
    fig.update_yaxes(
        title_text="Poverty Rate (%)",
        secondary_y=True,
        range=[-10, 100],
    )
    fig.update_layout(
        barmode="stack",
        title={
            'text': wrapped_title,
            'font': {'size': 16},
            'x': 0.5,
            'y': 0.92,
            'xanchor': 'center',
        },
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.03),
        annotations=[
            dict(
                xref="paper",
                yref="paper",
                x=-0.14,
                y=-0.2,
                text="Source: PEFA & Poverty Rate: World Bank",
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )
    return fig


def pefa_pillar_heatmap(df):
    fig_title = 'How did various pillars of the budget institutions change over time?'
    if df.empty:
        return empty_plot("PEFA by pillar data not available", fig_title)

    heatmap_data = df.melt(
        id_vars=['year'],
        value_vars=[col for col in df.columns if col.startswith('pillar')],
        var_name='pillar',
        value_name='score'
    )

    heatmap_data['grade'] = heatmap_data['score'].map(_score_to_grade)
    heatmap_data['pillar'] = heatmap_data['pillar'].map(PILLAR_MAPPING)

    heatmap_scores = heatmap_data.pivot(index='pillar', columns='year', values='score')
    heatmap_grades = heatmap_data.pivot(index='pillar', columns='year', values='grade')

    heatmap_scores.sort_index(ascending=False, inplace=True)
    heatmap_grades.sort_index(ascending=False, inplace=True)

    hover_text = heatmap_scores.applymap(lambda x: f"{x:.1f}" if not np.isnan(x) else "N/A")
    hover_text = hover_text + "<br>Grade: " + heatmap_grades.values

    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap_scores.values,
            x=heatmap_scores.columns,
            y=heatmap_scores.index,
            text=hover_text.values,
            hovertemplate=(
                "Year: %{x}<br>"
                "Pillar: %{y}<br>"
                "Score: %{text}<extra></extra>"
            ),
            colorscale='Viridis',
            zmin=1,
            zmax=4,
            colorbar=dict(
                title=dict(
                    text="PEFA Grades",
                    side='right',
                    font=dict(size=12),
                ),
                tickvals=list(SCORE_MAPPING.keys()),
                ticktext=list(SCORE_MAPPING.values()),
            ),
        )
    )

    fig.update_xaxes(
        tickvals=heatmap_scores.columns,
        ticktext=heatmap_scores.columns,
        title_text="",
        showgrid=False,
    )

    fig.update_yaxes(
        ticksuffix=" ",
        tickmode='linear',
        title_text="",
        showgrid=False,
    )

    fig.update_layout(
        title={
            'text': fig_title,
            'font': {'size': 16},
            'x': 0.5,
            'y': 0.9,
            'xanchor': 'center',
        },
    )
    return fig


def _score_to_grade(score):
    if np.isnan(score):
        return "N/A"
    return SCORE_MAPPING[min(SCORE_MAPPING.keys(), key=lambda x: abs(x - score))]

def pefa_narrative(df):
    if df.empty:
        return 'The Public Expenditure and Financial Accountability (PEFA) program provides a framework for assessing and reporting on the strengths and weaknesses of public financial management (PFM) using quantitative indicators to measure performance. Unfortunately, there is no PEFA accessment for this country to help us understand its quality of budget institutions.'

    country = df.country_name.iloc[0]
    earliest_year = df.year.min()
    earliest = df[df.year == earliest_year]
    latest_year = df.year.max()
    latest = df[df.year == latest_year]
    pillar_columns = [col for col in df.columns if col.startswith('pillar')]
    pillar_scores = latest[pillar_columns].iloc[0]

    highest_pillar = pillar_scores.idxmax()
    highest_score = pillar_scores.max()
    highest_grade = _score_to_grade(highest_score)

    lowest_pillar = pillar_scores.idxmin()
    lowest_score = pillar_scores.min()
    lowest_grade = _score_to_grade(lowest_score)

    text = f'''According to the latest Public Expenditure and Financial Accountability (PEFA) assessment conducted for {latest_year}, the strongest pillar of {country}’s budget institutions is "{_pillar_text(highest_pillar)}", with an average score of {highest_score:.1f} (Grade {highest_grade}){_strength_narrative(highest_pillar, highest_score)}. On the other hand, the pillar with the most room for improvement is "{_pillar_text(lowest_pillar)}", which scored {lowest_score:.1f} (Grade {lowest_grade}), {_weakness_narrative(lowest_pillar)}. '''

    if earliest_year != latest_year:
        improvement = (
            latest[pillar_columns].values[0] - earliest[pillar_columns].values[0]
        )

        most_improved_pillar = pillar_columns[np.nanargmax(improvement)]
        most_imporved_earliest_score = earliest[most_improved_pillar].iloc[0]
        most_imporved_earliest_grade = _score_to_grade(most_imporved_earliest_score)
        most_imporved_latest_score = latest[most_improved_pillar].iloc[0]
        most_imporved_latest_grade = _score_to_grade(most_imporved_latest_score)

        most_degraded_pillar = pillar_columns[np.nanargmin(improvement)]
        most_degraded_earliest_score = earliest[most_degraded_pillar].iloc[0]
        most_degraded_earliest_grade = _score_to_grade(most_degraded_earliest_score)
        most_degraded_latest_score = latest[most_degraded_pillar].iloc[0]
        most_degraded_latest_grade = _score_to_grade(most_degraded_latest_score)

        text += f'''Over time, the pillar that improved the most is "{_pillar_text(most_improved_pillar)}", which saw an increase from {most_imporved_earliest_score:.1f} (Grade {most_imporved_earliest_grade}) in {earliest_year} to {most_imporved_latest_score:.1f} (Grade {most_imporved_latest_grade}) in the latest assessment. Conversely, the pillar that degraded the most is "{_pillar_text(most_degraded_pillar)}" which fell from {most_degraded_earliest_score:.1f} (Grade {most_degraded_earliest_grade}) in {earliest_year} to {most_degraded_latest_score:.1f} (Grade {most_degraded_latest_grade}) in the latest scores. '''

    text += "These insights underscore areas of strength to build upon and critical weaknesses requiring targeted reforms."

    return text

def _strength_narrative(pillar, score):
    narratives = PILLAR_NARRARIVE_MAPPING[pillar]
    if score > 2.75:
        text = ', reflecting '
        text += narratives[0]
    else:
        text = '; despite being the strongest pillar, its low rating signals challenges in '
        text += narratives[1]
    return text

def _weakness_narrative(pillar):
    return f'indicating challenges in {PILLAR_NARRARIVE_MAPPING[pillar][1]}'

def _pillar_text(pillar):
    return re.sub(r'^\d+\.\s+', '', PILLAR_MAPPING[pillar])
