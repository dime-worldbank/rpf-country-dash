import dash
from dash import html, callback, Input, Output

from pages.about_content_en import get_layout as get_layout_en
from pages.about_content_fr import get_layout as get_layout_fr
from pages.about_content_pt import get_layout as get_layout_pt

dash.register_page(__name__)

layout = html.Div(id="about-content")


@callback(
    Output("about-content", "children"),
    Input("stored-language", "data"),
)
def render_about(lang):
    lang = lang or "en"
    if lang == "fr":
        return get_layout_fr()
    if lang == "pt":
        return get_layout_pt()
    return get_layout_en()
