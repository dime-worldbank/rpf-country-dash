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


def _locative_fr(name):
    """French locative: transform a country name into its "in X" form.

    Unlike English "in", French uses different prepositions depending on
    the country's gender, number, and whether it takes an article:

    * ``le Kenya``       → ``au Kenya``      (à + le → au)
    * ``les États-Unis`` → ``aux États-Unis`` (à + les → aux)
    * ``la France``      → ``en France``      (feminine drops article)
    * ``l'Albanie``      → ``en Albanie``     (vowel drops article)
    * ``Cuba``           → ``à Cuba``          (no article → à)

    The returned form is capitalized since most consumers use it at the
    start of a sentence ("Au Kenya, …", "En Albanie, …").
    """
    if not name:
        return name
    if name.startswith("les "):
        result = "aux " + name[4:]
    elif name.startswith("le "):
        result = "au " + name[3:]
    elif name.startswith("la "):
        result = "en " + name[3:]
    elif name.startswith("l'"):
        result = "en " + name[2:]
    else:
        # No article (e.g. "Cuba", "Haïti") — prepend "à"
        result = "à " + name
    # Capitalize first letter (E/A) for sentence-start usage
    return result[0].upper() + result[1:]


def elide_que(lang, name):
    """Return "que" or "qu'" depending on the first character of *name*.

    French elides "que" to "qu'" before a vowel sound — required in
    templates like "tandis que {name}" where {name} could start with
    any letter (e.g. a region name like "Afar" or "Asmara"):

    * ``elide_que("fr", "Afar")``  → ``"qu'"``
    * ``elide_que("fr", "Kampala")`` → ``"que "``
    * ``elide_que("en", …)`` → ``"that"`` (no elision in English)
    """
    if lang != "fr" or not name:
        return "que "
    first = name[0].lower()
    if first in _FRENCH_VOWELS:
        return "qu'"
    return "que "


def locative(lang, name):
    """Return the locative ("in X") form of *name* in the given language.

    The locative role expresses location ("in X"). English uses "in X"
    uniformly, but French distinguishes between au/aux/en/à depending on
    gender and number — see :func:`_locative_fr`.

    The result is capitalized so callers can drop it directly at the
    start of a sentence ("Au Kenya, …", "In Kenya, …").

    Parameters
    ----------
    lang : str
        Language code ("en", "fr", …).
    name : str
        The country or place name. For French, should include the article
        ("le Kenya", "la France", "l'Albanie", "les États-Unis") so this
        helper can pick the right preposition. For other languages, a
        plain name works.
    """
    if not name:
        return name
    if lang == "fr":
        return _locative_fr(name)
    if lang == "en":
        return "In " + name
    return name


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
