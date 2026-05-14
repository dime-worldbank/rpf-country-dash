from dash import html
import dash_bootstrap_components as dbc
from translations import t


def disclaimer_tooltip(disclaimer_id, tooltip_text, lang="en"):
    return html.Div(
        [
            html.Span(
                t("disclaimer.label", lang),
                id=disclaimer_id,
                style={
                    "color": "CCCCCC",
                    "fontSize": "12px",
                    "textDecoration": "underline dotted",
                    "cursor": "pointer",
                    "fontWeight": "bold",
                    "marginLeft": "8px",
                },
            ),
            dbc.Tooltip(
                tooltip_text,
                target=disclaimer_id,
                placement="top",
                style={"fontSize": "14px"},
                className='disclaimer-tooltip'
            ),
        ],
        style={"display": "flex", "alignItems": "center"},
    )
