"""Page title above the "Over time / Across space" tabs.

"<Country>'s public finances in numbers", following the selected country and
language. Each tabbed page places ``country_title(page)`` at the top of its
card and calls ``register_country_title(page)`` once at import to wire the
callback.
"""
from dash import Input, Output, callback, html

from translations import genitive, t


def title_text(country, lang="en"):
    lang = lang or "en"
    if not country:
        return t("heading.finances_in_numbers", lang)
    return t(
        "heading.country_finances_in_numbers", lang,
        country=t(f"country.{country}", lang),
        # The catalog entry carries gender/number, so French and Portuguese
        # get the right contraction (du Togo, de la Tunisie, do Togo).
        country_gen=genitive(lang, t(f"country.{country}", lang, meta=True)),
    )


def country_title(page):
    """The heading for one page; the registered callback fills its text."""
    return html.H4(id=f"{page}-country-title", className="country-title")


def register_country_title(page):
    @callback(
        Output(f"{page}-country-title", "children"),
        Input("country-select", "value"),
        Input("stored-language", "data"),
    )
    def update_country_title(country, lang):
        return title_text(country, lang)
