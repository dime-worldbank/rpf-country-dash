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

FUNC_PALETTE = QUALITATIVE
FUNC_COLORS = create_category_color_map(COFOG_CATS, palette="qualitative")

MAP_DISCLAIMER = (
    "Country borders or names do not necessarily reflect the World Bank Group's "
    "official position. This map is for illustrative purposes and does not imply "
    "the expression of any opinion on the part of the World Bank, concerning the "
    "legal status of any country or territory or concerning the delimitation of "
    "frontiers or boundaries."
)
