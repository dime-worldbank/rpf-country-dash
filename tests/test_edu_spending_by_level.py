import unittest

import pandas as pd

import server_store
import components.edu_spending_by_level as esl


def _walk_layout(node):
    """Every component in a layout tree (children may be a list or one node)."""
    yield node
    children = getattr(node, "children", None)
    if children is None or isinstance(children, str):
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        if not isinstance(child, (str, int, float)):
            yield from _walk_layout(child)


def _spending_row(year, econ, value, func_sub="Primary Education"):
    return dict(
        country_name="Testland",
        year=year,
        func_sub=func_sub,
        econ=econ,
        per_capita_real_expenditure=value,
    )


class TestReportedYearsAreConsistent(unittest.TestCase):
    """The chart, the narrative and the shared axis must agree on which years
    count as reported. They diverged once: the narrative applied the
    drop-0/NaN rule per econ-category row while the chart applied it to the
    per-year total, so categories that netted to zero stayed in the averages
    but never reached the line.
    """

    def setUp(self):
        server_store.set(
            "basic_country_info", {"Testland": {"currency_code": "USD"}}
        )
        # A single-row outcome frame keeps build_relationship_sentence out of the
        # narrative (it needs 2+ overlapping points), so these assertions are
        # about the spending sentence alone.
        server_store.set(
            "completion_rates",
            pd.DataFrame(
                [dict(country_name="Testland", year=2021, completion_rate_primary=50.0)]
            ),
        )

    def tearDown(self):
        server_store.clear()

    def _chart_points(self, econ_filter=esl.ALL_ECON):
        fig = esl.spending_figure("Testland", econ_filter, "en")
        return {
            int(year): value
            for trace in fig.data
            for year, value in zip(trace.x, trace.y)
        }

    def test_offsetting_categories_drop_from_chart_and_narrative_alike(self):
        # 2020's two categories net to zero: not reported, on both paths.
        server_store.set(
            "edu_func_sub_econ_expenditure",
            pd.DataFrame(
                [
                    _spending_row(2020, "Wage bill", 100.0),
                    _spending_row(2020, "Subsidies", -100.0),
                    _spending_row(2021, "Wage bill", 200.0),
                    _spending_row(2022, "Wage bill", 200.0),
                ]
            ),
        )

        points = self._chart_points()
        self.assertEqual(points, {2021: 200.0, 2022: 200.0})

        narrative = esl.spending_narrative("Testland", esl.ALL_ECON, "completion_rate", "en")
        # The average the narrative quotes is the average of the plotted points.
        self.assertIn("200.00 USD", narrative)
        self.assertIn("between 2021 and 2022", narrative)
        self.assertNotIn("2020", narrative)

    def test_summed_categories_are_reported_even_when_one_row_is_zero(self):
        # A zero row alongside a real one must not remove the year: the total
        # is what's reported, and 150 is what the chart draws.
        server_store.set(
            "edu_func_sub_econ_expenditure",
            pd.DataFrame(
                [
                    _spending_row(2021, "Wage bill", 150.0),
                    _spending_row(2021, "Subsidies", 0.0),
                    _spending_row(2022, "Wage bill", 150.0),
                ]
            ),
        )

        self.assertEqual(self._chart_points(), {2021: 150.0, 2022: 150.0})
        narrative = esl.spending_narrative("Testland", esl.ALL_ECON, "completion_rate", "en")
        self.assertIn("150.00 USD", narrative)

    def test_axis_spans_only_reported_years(self):
        # The axis must not dangle past the last plotted point.
        server_store.set(
            "edu_func_sub_econ_expenditure",
            pd.DataFrame(
                [
                    _spending_row(2020, "Wage bill", 0.0),
                    _spending_row(2021, "Wage bill", 200.0),
                    _spending_row(2022, "Wage bill", 300.0),
                ]
            ),
        )

        fig = esl.spending_figure("Testland", esl.ALL_ECON, "en")
        # Range 2020.5–2022.5 = reported bounds (2021, 2022); the 0-value 2020 is excluded.
        self.assertEqual(tuple(fig.layout.xaxis.range), (2020.5, 2022.5))

    def test_outcome_chart_stands_alone_when_the_filter_leaves_no_spending(self):
        # Education spending is reported only under 'Wage bill'.
        server_store.set(
            "edu_func_sub_econ_expenditure",
            pd.DataFrame([_spending_row(2019, "Wage bill", 100.0)]),
        )
        server_store.set(
            "completion_rates",
            pd.DataFrame(
                [
                    dict(country_name="Testland", year=year, completion_rate_primary=50.0)
                    for year in (2015, 2016, 2017)
                ]
            ),
        )

        fig = esl.outcome_figure("Testland", "Capital expenditures", "completion_rate", "en")

        # The indicator is still worth reading with no spending to align to...
        self.assertTrue(fig.data)
        # ...over its own years, and still on whole-year ticks.
        self.assertEqual(tuple(fig.layout.xaxis.range), (2014.5, 2017.5))
        self.assertEqual(fig.layout.xaxis.dtick, 1)
        self.assertEqual(fig.layout.xaxis.tickformat, "d")

    def test_outcome_chart_shares_the_spending_window_when_there_is_one(self):
        server_store.set(
            "edu_func_sub_econ_expenditure",
            pd.DataFrame(
                [_spending_row(2019, "Wage bill", 100.0), _spending_row(2020, "Wage bill", 120.0)]
            ),
        )
        server_store.set(
            "completion_rates",
            pd.DataFrame(
                [
                    dict(country_name="Testland", year=year, completion_rate_primary=50.0)
                    for year in range(2015, 2023)
                ]
            ),
        )

        fig = esl.outcome_figure("Testland", esl.ALL_ECON, "completion_rate", "en")

        # Clamped to the spending years, not the indicator's wider history.
        self.assertEqual(tuple(fig.layout.xaxis.range), (2018.5, 2020.5))

    def test_all_unreported_yields_the_same_empty_state_on_both_paths(self):
        server_store.set(
            "edu_func_sub_econ_expenditure",
            pd.DataFrame(
                [
                    _spending_row(2021, "Wage bill", 0.0),
                    _spending_row(2022, "Wage bill", None),
                ]
            ),
        )

        self.assertEqual(self._chart_points(), {})
        self.assertEqual(
            esl.spending_narrative("Testland", esl.ALL_ECON, "completion_rate", "en"),
            "No data available for this period",
        )


class TestOutcomeAutoSelectHint(unittest.TestCase):
    """The hint under the indicator dropdown appears only when the indicator
    was auto-selected from the economic category, never after a manual pick.
    """

    ECON = f"{esl.ECON_FILTER_ID}.value"
    OUTCOME = f"{esl.OUTCOME_FILTER_ID}.value"

    def test_category_change_autoselects_and_shows_hint(self):
        value, hint = esl.sync_outcome_indicator(
            "Wage bill", {self.ECON: esl.ECON_FILTER_ID}, "en"
        )
        self.assertEqual(value, "teacher_salary")
        self.assertEqual(hint, "↳ Recommended for Wage bill")

    def test_manual_pick_keeps_value_and_clears_hint(self):
        value, hint = esl.sync_outcome_indicator(
            "Wage bill", {self.OUTCOME: esl.OUTCOME_FILTER_ID}, "en"
        )
        self.assertIs(value, esl.no_update)
        self.assertIsNone(hint)

    def test_chained_change_counts_as_autoselect(self):
        # Category and indicator both in the trigger set: the indicator changed
        # because the category did, so it is still an auto-selection.
        value, hint = esl.sync_outcome_indicator(
            "Capital expenditures",
            {self.ECON: esl.ECON_FILTER_ID, self.OUTCOME: esl.OUTCOME_FILTER_ID},
            "en",
        )
        self.assertEqual(value, "electricity")
        self.assertEqual(hint, "↳ Recommended for Capital expenditures")

    def test_initial_load_and_all_categories_have_no_hint(self):
        value, hint = esl.sync_outcome_indicator(esl.ALL_ECON, {}, "en")
        self.assertEqual(value, esl.DEFAULT_OUTCOME)
        self.assertIsNone(hint)

    def test_hint_is_translated(self):
        self.assertEqual(
            esl.outcome_hint("Wage bill", "fr"),
            "↳ Recommandé pour Masse salariale",
        )
        self.assertEqual(
            esl.outcome_hint("Wage bill", "pt"),
            "↳ Recomendado para Folha salarial",
        )

    def test_layout_has_hint_slot_under_indicator(self):
        ids = [getattr(n, "id", None) for n in _walk_layout(esl.layout("en"))]
        self.assertIn(esl.OUTCOME_HINT_ID, ids)


class TestLinkedHoverWiring(unittest.TestCase):
    """The linked-hover callback relies on both graphs clearing hoverData on
    unhover (so leaving one chart clears its mirror) and on its dummy output
    store being in the layout.
    """

    def test_both_graphs_clear_on_unhover_and_store_present(self):
        nodes = list(_walk_layout(esl.layout("en")))
        self.assertIn(esl.HOVER_SYNC_ID, [getattr(n, "id", None) for n in nodes])
        for chart_id in (esl.SPENDING_CHART_ID, esl.OUTCOME_CHART_ID):
            # The container div shares the graph's id; only the Graph has the prop.
            graphs = [
                n for n in nodes
                if getattr(n, "id", None) == chart_id and hasattr(n, "clear_on_unhover")
            ]
            self.assertEqual(len(graphs), 1, chart_id)
            self.assertTrue(graphs[0].clear_on_unhover, chart_id)


if __name__ == "__main__":
    unittest.main()
