from translations.en import TRANSLATIONS as EN
from translations.fr import TRANSLATIONS as FR

_LANGUAGES = {
    "en": EN,
    "fr": FR,
}

LANGUAGE_OPTIONS = [
    {"label": "English", "value": "en"},
    {"label": "Français", "value": "fr"},
]

DEFAULT_LANGUAGE = "en"


def t(key, lang=None, **kwargs):
    """Look up a translation key for the given language.

    Parameters
    ----------
    key : str
        Dot-separated translation key, e.g. "nav.overview".
    lang : str, optional
        Language code ("en", "fr"). Falls back to DEFAULT_LANGUAGE.
    **kwargs :
        Values to interpolate into the template string via str.format().

    Returns
    -------
    str
        The translated (and optionally interpolated) string.
    """
    if lang is None:
        lang = DEFAULT_LANGUAGE
    translations = _LANGUAGES.get(lang, _LANGUAGES[DEFAULT_LANGUAGE])
    template = translations.get(key, _LANGUAGES[DEFAULT_LANGUAGE].get(key, key))
    if kwargs:
        return template.format(**kwargs)
    return template


def get_available_languages():
    """Return list of supported language codes."""
    return list(_LANGUAGES.keys())
