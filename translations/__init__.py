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


# ---------------------------------------------------------------------------
# Grammar helpers — language-specific utilities for interpolated values
# ---------------------------------------------------------------------------

_FRENCH_VOWELS = frozenset("aeiouyàâéèêëïîôùûüœæ")


def _genitive_fr(name):
    """French genitive: prefix *name* with the right form of "de".

    * ``de + le``  → ``du``   (e.g. "du taux")
    * ``de + les`` → ``des``  (e.g. "des dépenses")
    * ``de + la``  → ``de la`` (no contraction)
    * ``de + l'``  → ``de l'`` (no contraction)
    * ``de`` + consonant-initial bare noun → ``de …``
    * ``de`` + vowel-initial bare noun → ``d'…`` (elision)
    """
    if not name:
        return name
    if name.startswith("les "):
        return "des " + name[4:]
    if name.startswith("le "):
        return "du " + name[3:]
    if name.startswith(("la ", "l'")):
        return "de " + name
    first = name[0].lower()
    if first in _FRENCH_VOWELS:
        return "d'" + name
    return "de " + name


def genitive(lang, name):
    """Return the genitive ("of X") form of *name* in the given language.

    The genitive role expresses attribution or origin: "of X" in English,
    "de X" (with contractions and elision) in French. Use this when you
    need to interpolate a noun after a "de"/"of" preposition in a template.

    Parameters
    ----------
    lang : str
        Language code ("en", "fr", …).
    name : str
        The noun or noun phrase to prefix. May include an article
        ("le taux", "les dépenses", "l'indice") or be a bare noun.

    Returns
    -------
    str
        The correctly prefixed form:

        * French: handles article contractions (de+le→du, de+les→des) and
          vowel elision (d'économies vs. de prix).
        * English: prepends "of ".
        * Other: returns *name* unchanged.
    """
    if not name:
        return name
    if lang == "fr":
        return _genitive_fr(name)
    if lang == "en":
        return "of " + name
    return name
