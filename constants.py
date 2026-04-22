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


def translate_func(name, lang="en", narrative=False):
    """Translate a raw COFOG func name (e.g. "Health") to *lang*.

    * ``narrative=False`` → bare label form ("Santé", "Health") for
      chart legends and axis labels.
    * ``narrative=True`` → lowercase + articled prose form ("la santé",
      "health") for mid-sentence use like "dans la santé et la défense".

    Falls back to the raw name if *name* isn't in COFOG_KEY_MAP, and to
    the bare form if no ``.narrative`` variant is registered.
    """
    key = COFOG_KEY_MAP.get(name)
    if not key:
        return name
    if narrative:
        val = t(f"{key}.narrative", lang)
        # t() returns the key itself when missing — detect and fall back.
        if val != f"{key}.narrative":
            return val
    return t(key, lang)


def translate_econ(name, lang="en", narrative=False):
    """Translate a raw econ category name (e.g. "Wage bill") to *lang*.

    Same shape as :func:`translate_func` — see that function's docstring.
    """
    key = ECON_KEY_MAP.get(name)
    if not key:
        return name
    if narrative:
        val = t(f"{key}.narrative", lang)
        if val != f"{key}.narrative":
            return val
    return t(key, lang)


# Maps COFOG sub-function values (the `func_sub` column) to their
# translation keys. These are the leaf-level categories shown in the
# treemap on Education/Health subnational pages. Values come from the
# dataset query in queries.py and include categories spanning several
# COFOG families (Education, Health, Economic affairs, Public order, ...).
FUNC_SUB_KEY_MAP = {
    "Agriculture":                           "func_sub.agriculture",
    "Air Transport":                         "func_sub.air_transport",
    "Energy":                                "func_sub.energy",
    "Judiciary":                             "func_sub.judiciary",
    "Post-Secondary Non-Tertiary Education": "func_sub.post_secondary",
    "Primary Education":                     "func_sub.primary_education",
    "Primary and Secondary Health":          "func_sub.primary_secondary_health",
    "Primary and Secondary education":       "func_sub.primary_secondary_education",
    "Public Safety":                         "func_sub.public_safety",
    "Railroads":                             "func_sub.railroads",
    "Roads":                                 "func_sub.roads",
    "Secondary Education":                   "func_sub.secondary_education",
    "Telecom":                               "func_sub.telecom",
    "Tertiary Education":                    "func_sub.tertiary_education",
    "Tertiary and Quaternary Health":        "func_sub.tertiary_quaternary_health",
    "Transport":                             "func_sub.transport",
    "Water Supply":                          "func_sub.water_supply",
    "Water Transport":                       "func_sub.water_transport",
}


def translate_func_sub(name, lang="en"):
    """Translate a COFOG sub-function name (e.g. "Primary Education") to *lang*.

    Falls back to the raw name if it's not in FUNC_SUB_KEY_MAP. Used by
    the treemap on subnational Education / Health pages.
    """
    key = FUNC_SUB_KEY_MAP.get(name)
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
