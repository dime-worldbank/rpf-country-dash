from translations import t
from viz_theme import QUALITATIVE, create_category_color_map


START_YEAR = 2010

TREND_THRESHOLDS = 0.4


def get_map_disclaimer(lang="en"):
    return t("disclaimer.map", lang)


COFOG_CATS = [
    "Social protection",
    "Recreation, culture and religion",
    "Public order and safety",
    "Housing and community amenities",
    "Health",
    "General public services",
    "Environmental protection",
    "Education",
    "Economic affairs",
    "Defence",
]

# Maps the raw English COFOG data values (as they appear in the dataset's
# `func` column) to the translation key used in en.py/fr.py. Needed because
# the short translation keys ("cofog.recreation") don't match the full
# English labels ("Recreation, culture and religion") algorithmically.
COFOG_KEY_MAP = {
    "Social protection":               "cofog.social_protection",
    "Recreation, culture and religion": "cofog.recreation",
    "Public order and safety":         "cofog.public_order",
    "Housing and community amenities": "cofog.housing",
    "Health":                          "cofog.health",
    "General public services":         "cofog.general_public",
    "Environmental protection":        "cofog.environment",
    "Education":                       "cofog.education",
    "Economic affairs":                "cofog.economic",
    "Defence":                         "cofog.defence",
}

# Maps raw English econ data values (the `econ` column in the dataset) to
# the translation key used in en.py/fr.py. Includes both the raw dataset
# values and the synthetic bucket names created by
# func_operational_vs_capital_spending.prepare_prop_econ_by_func_df()
# (which remaps "everything except Wage bill and Capital expenditures"
# into a single "Non-wage recurrent" bucket).
ECON_KEY_MAP = {
    "Capital expenditures":         "econ.capital_expenditures",
    "Goods and services":           "econ.goods_services",
    "Social benefits":              "econ.social_benefits",
    "Subsidies":                    "econ.subsidies",
    "Wage bill":                    "econ.wage_bill",
    "Interest on debt":             "econ.interest_debt",
    "Other grants and transfers":   "econ.grants_transfers",
    "Other expenses":               "econ.other_expenses",
    "Non-wage recurrent":           "econ.non_wage_recurrent",
}


def translate_func(name, lang="en"):
    """Translate a raw COFOG func name (e.g. "Health") to *lang*.

    Falls back to the raw name if it's not in COFOG_KEY_MAP — safer than
    raising, since a future dataset value would silently pass through.
    Used by chart code (legend names, hover text) and narrative helpers.
    """
    key = COFOG_KEY_MAP.get(name)
    return t(key, lang) if key else name


def translate_econ(name, lang="en"):
    """Translate a raw econ category name (e.g. "Wage bill") to *lang*.

    Translation keys in en.py/fr.py already capture the display-label
    transformation (e.g. "Wage bill" → "Employees compensation" →
    "Rémunération des employés"), so this is a single lookup. Falls back
    to the raw name if unregistered.
    """
    key = ECON_KEY_MAP.get(name)
    return t(key, lang) if key else name

FUNC_PALETTE = QUALITATIVE
FUNC_COLORS = create_category_color_map(COFOG_CATS, palette="qualitative")

MAP_DISCLAIMER = (
    "Country borders or names do not necessarily reflect the World Bank Group's "
    "official position. This map is for illustrative purposes and does not imply "
    "the expression of any opinion on the part of the World Bank, concerning the "
    "legal status of any country or territory or concerning the delimitation of "
    "frontiers or boundaries."
)
