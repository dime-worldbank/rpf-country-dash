from enum import Enum
import plotly.express as px


START_YEAR = 2000

TREND_THRESHOLDS = 0.4

NARRATIVE_ERROR_TEMPLATES = {
    "DATA_UNAVAILABLE": "Data not available for this period.",
    "DATA_UNAVAILABLE_DATASET_NAME": "{dataset_name} data not available for this period.",
    "GENERIC_ERROR": "An error occurred while processing the data.",
}

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
FUNC_PALETTE = px.colors.qualitative.T10
FUNC_COLORS = {
    cat: FUNC_PALETTE[i % len(FUNC_PALETTE)] for i, cat in enumerate(COFOG_CATS)
}

MAP_DISCLAIMER = "Country borders or names do not necessarily reflect the World Bank Group's official position." \
"This map is for illustrative purposes and does not imply the expression of any opinion on the part of the World Bank," \
"concerning the legal status of any country or territory or concerning the delimitation of frontiers or boundaries."
