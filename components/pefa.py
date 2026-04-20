from collections import OrderedDict
from plotly.subplots import make_subplots
from translations import t, genitive
from utils import empty_plot
import numpy as np
import plotly.graph_objects as go
import re
import textwrap
from viz_theme import SEQUENTIAL_SCALE

SCORE_MAPPING = OrderedDict([
    (4, "A"),
    (3, "B"), (3.5, "B+"),
    (2, "C"), (2.5, "C+"),
    (1, "D"), (1.5, "D+"),
])

PILLAR_KEYS = OrderedDict([
    ('pillar1_budget_reliability', 'pefa.pillar1'),
    ('pillar2_transparency', 'pefa.pillar2'),
    ('pillar3_asset_liability', 'pefa.pillar3'),
    ('pillar4_policy_based_budget', 'pefa.pillar4'),
    ('pillar5_predictability_and_control', 'pefa.pillar5'),
    ('pillar6_accounting_and_reporting', 'pefa.pillar6'),
    ('pillar7_external_audit', 'pefa.pillar7'),
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


def _get_pillar_name(pillar, lang="en"):
    """Get the translated pillar name."""
    key = PILLAR_KEYS.get(pillar)
    if key:
        return t(key, lang)
    return PILLAR_MAPPING.get(pillar, pillar)


def _get_pillar_mapping(lang="en"):
    """Get a mapping from column names to translated pillar names."""
    return OrderedDict([
        (col, _get_pillar_name(col, lang)) for col in PILLAR_KEYS
    ])


def pefa_overall_figure(df, pov_df, lang="en"):
    title_text = t("chart.pefa_overall", lang)
    wrapped_title = "<br>".join(textwrap.wrap(title_text, width=45))
    if df.empty:
        return empty_plot(t("error.pefa_unavailable", lang), wrapped_title)

    pillar_columns = [col for col in df.columns if col.startswith('pillar')]
    overall_scores = df[pillar_columns].mean(axis=1)

    overall_grades = overall_scores.map(_score_to_grade)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            name=t("trace.poverty_rate", lang),
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
            name=t("trace.pefa_score", lang),
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
        title_text=t("axis.quality_budget_institutions", lang),
        secondary_y=False,
        tickvals=list(SCORE_MAPPING.keys()),
        ticktext=list(SCORE_MAPPING.values()),
        range=[0, 4.5],
    )
    fig.update_yaxes(
        title_text=t("axis.poverty_rate", lang),
        secondary_y=True,
        range=[-10, 100],
    )
    fig.update_layout(
        barmode="stack",
        title={
            'text': wrapped_title,
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
                text=t("source.pefa_poverty", lang),
                showarrow=False,
                font=dict(size=12),
            )
        ],
    )
    return fig


def pefa_pillar_heatmap(df, lang="en"):
    fig_title = t("chart.pefa_by_pillar", lang)
    if df.empty:
        return empty_plot(t("error.pefa_pillar_unavailable", lang), fig_title)

    pillar_mapping = _get_pillar_mapping(lang)

    heatmap_data = df.melt(
        id_vars=['year'],
        value_vars=[col for col in df.columns if col.startswith('pillar')],
        var_name='pillar',
        value_name='score'
    )

    heatmap_data['grade'] = heatmap_data['score'].map(_score_to_grade)
    heatmap_data['pillar'] = heatmap_data['pillar'].map(pillar_mapping)

    heatmap_scores = heatmap_data.pivot(index='pillar', columns='year', values='score')
    heatmap_grades = heatmap_data.pivot(index='pillar', columns='year', values='grade')

    heatmap_scores.sort_index(ascending=False, inplace=True)
    heatmap_grades.sort_index(ascending=False, inplace=True)

    hover_text = heatmap_scores.map(lambda x: f"{x:.1f}" if not np.isnan(x) else "N/A")
    hover_text = hover_text + f"<br>{t('hover.grade', lang)}: " + heatmap_grades.values

    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap_scores.values,
            x=heatmap_scores.columns,
            y=heatmap_scores.index,
            text=hover_text.values,
            hovertemplate=(
                f"{t('hover.year', lang)}: %{{x}}<br>"
                f"{t('hover.pillar', lang)}: %{{y}}<br>"
                f"{t('hover.score', lang)}: %{{text}}<extra></extra>"
            ),
            colorscale=SEQUENTIAL_SCALE,
            zmin=1,
            zmax=4,
            colorbar=dict(
                title=dict(
                    text=t("pefa.grades", lang),
                    side='right',
                ),
                tickvals=list(SCORE_MAPPING.keys()),
                ticktext=list(SCORE_MAPPING.values()),
                outlinewidth=0,
            ),
        )
    )

    fig.update_xaxes(
        tickvals=heatmap_scores.columns,
        ticktext=heatmap_scores.columns,
        title_text="",
    )

    fig.update_yaxes(
        ticksuffix=" ",
        tickmode='linear',
        title_text="",
    )

    fig.update_layout(
        title={
            'text': fig_title,
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

def pefa_narrative(df, lang="en"):
    if df.empty:
        return t("narrative.pefa_no_data", lang)

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

    strength_narrative = _strength_narrative(highest_pillar, highest_score, lang)
    weakness_narrative = _weakness_narrative(lowest_pillar, lang)

    highest_pillar_name = _pillar_text(highest_pillar, lang)
    lowest_pillar_name = _pillar_text(lowest_pillar, lang)

    country_display = t(f"country.{country}", lang)
    text = t("narrative.pefa_latest", lang,
             year=latest_year, country=country_display,
             country_gen=genitive(lang, country_display),
             highest_pillar=highest_pillar_name, highest_score=highest_score,
             highest_grade=highest_grade, strength_narrative=strength_narrative,
             lowest_pillar=lowest_pillar_name, lowest_score=lowest_score,
             lowest_grade=lowest_grade, weakness_narrative=weakness_narrative)

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

        improved_name = _pillar_text(most_improved_pillar, lang)
        degraded_name = _pillar_text(most_degraded_pillar, lang)

        text += t("narrative.pefa_over_time", lang,
                   improved_pillar=improved_name,
                   improved_earliest_score=most_imporved_earliest_score,
                   improved_earliest_grade=most_imporved_earliest_grade,
                   earliest_year=earliest_year,
                   improved_latest_score=most_imporved_latest_score,
                   improved_latest_grade=most_imporved_latest_grade,
                   degraded_pillar=degraded_name,
                   degraded_earliest_score=most_degraded_earliest_score,
                   degraded_earliest_grade=most_degraded_earliest_grade,
                   degraded_latest_score=most_degraded_latest_score,
                   degraded_latest_grade=most_degraded_latest_grade)

    text += t("narrative.pefa_conclusion", lang)

    return text

def _strength_narrative(pillar, score, lang="en"):
    # Map pillar keys to translation key prefixes
    pillar_num = pillar.split("_")[0].replace("pillar", "")
    if score > 2.75:
        text = t("narrative.pefa_strength_high", lang)
        text += t(f"pefa.pillar{pillar_num}.desc", lang)
    else:
        text = t("narrative.pefa_strength_low", lang)
        text += t(f"pefa.pillar{pillar_num}.gerund", lang)
    return text

def _weakness_narrative(pillar, lang="en"):
    pillar_num = pillar.split("_")[0].replace("pillar", "")
    return t("narrative.pefa_weakness", lang) + t(f"pefa.pillar{pillar_num}.gerund", lang)

def _pillar_text(pillar, lang="en"):
    pillar_name = _get_pillar_name(pillar, lang)
    return re.sub(r'^\d+\.\s+', '', pillar_name)
