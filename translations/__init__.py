import re
import string

from babel.numbers import get_currency_name

from translations.en import TRANSLATIONS as EN
from translations.fr import TRANSLATIONS as FR
from translations.pt import TRANSLATIONS as PT

_LANGUAGES = {
    "en": EN,
    "fr": FR,
    "pt": PT,
}

LANGUAGE_OPTIONS = [
    {"label": "English", "value": "en"},
    {"label": "Français", "value": "fr"},
    {"label": "Português (Brasil)", "value": "pt"},
]

DEFAULT_LANGUAGE = "en"


# Matches a digit-dot-digit sequence — used to swap English decimal points
# for comma-decimal languages inside *substituted values only*.
_DECIMAL_RE = re.compile(r"(\d)\.(\d)")


class _CommaDecimalFormatter(string.Formatter):
    """str.format with comma-decimal number localization applied per-field.

    The key property is that ``format_field`` is invoked once per ``{…}``
    placeholder during rendering, receiving only the value being
    substituted — the surrounding template text never passes through
    this hook. So:

    * ``{x:.1f}`` with float ``23.4`` → ``"23,4"``
    * ``{x}`` with float ``0.73`` → ``"0,73"``
    * ``{corr}`` with a caller-preformatted string ``"0.73"`` → ``"0,73"``
    * ``{country}`` with ``"le Kenya"`` → unchanged (no digit-dot-digit)
    * A pillar label like ``"1. Fiabilité du budget"`` inside the template
      text is left completely alone because it isn't a substituted value.
    """

    def format_field(self, value, format_spec):
        result = super().format_field(value, format_spec)
        if _DECIMAL_RE.search(result):
            result = _DECIMAL_RE.sub(r"\1,\2", result)
        return result


_COMMA_DECIMAL_FORMATTER = _CommaDecimalFormatter()
_COMMA_DECIMAL_LANGS = {"fr", "pt"}

_CURRENCY_LOCALES = {
    "fr": "fr_FR",
    "pt": "pt_BR",
}


def t(key, lang=None, meta=False, **kwargs):
    """Look up a translation key for the given language.

    Parameters
    ----------
    key : str
        Dot-separated translation key, e.g. "nav.overview".
    lang : str, optional
        Language code ("en", "fr", "pt"). Falls back to DEFAULT_LANGUAGE.
    meta : bool, default False
        Return the catalog entry whole instead of just its display name.
        Nouns in the French and Portuguese catalogs are stored as
        ``{"name", "plural", "feminine"}`` dicts; trend-narrative agrees
        verbs and participles off those flags, and a bare name silently
        defaults to singular/masculine ("les dépenses réelles a augmenté").
        Pass ``meta=True`` when handing a noun to trend-narrative; leave it
        False everywhere the value is rendered as text.
    **kwargs :
        Values to interpolate into the template string via str.format().

    Returns
    -------
    str or dict
        The translated string, or — with ``meta=True`` — the raw catalog
        entry: a dict where the language carries grammatical metadata, a
        plain string where it doesn't (English). For French and Portuguese,
        numeric-looking substituted values render with comma decimals
        (see :class:`_CommaDecimalFormatter`).
    """
    if lang is None:
        lang = DEFAULT_LANGUAGE
    translations = _LANGUAGES.get(lang, _LANGUAGES[DEFAULT_LANGUAGE])
    template = translations.get(key, _LANGUAGES[DEFAULT_LANGUAGE].get(key, key))

    if meta:
        return template

    # If template is a dict (metadata), extract the display name for template rendering
    if isinstance(template, dict):
        template = template.get("name", str(template))

    if not kwargs:
        return template
    if lang in _COMMA_DECIMAL_LANGS:
        return _COMMA_DECIMAL_FORMATTER.vformat(template, (), kwargs)
    return template.format(**kwargs)


def get_available_languages():
    """Return list of supported language codes."""
    return list(_LANGUAGES.keys())


def localize_currency_name(currency_name, lang=None, currency_code=None):
    """Return a Babel-localized currency name for supported languages."""
    if lang is None:
        lang = DEFAULT_LANGUAGE

    locale = _CURRENCY_LOCALES.get(lang)
    if locale and currency_code:
        return get_currency_name(currency_code, count=2, locale=locale)

    return currency_name or currency_code or ""


# ---------------------------------------------------------------------------
# Grammar helpers — language-specific utilities for interpolated values
# ---------------------------------------------------------------------------

_FRENCH_VOWELS = frozenset("aeiouyàâéèêëïîôùûüœæ")

_FR_ARTICLES = ("les ", "le ", "la ", "l'")
_PT_ARTICLES = ("os ", "as ", "o ", "a ")


def strip_article(lang, name):
    """Strip the leading article from *name* for the given language.

    Used when a localized noun phrase needs to appear without its article
    — e.g. dropdown labels that show "Kenya" / "Albanie" rather than
    "le Kenya" / "l'Albanie", even though the articled form is what the
    translations dict stores (because mid-sentence narratives need it).

    Currently handles French and Portuguese articles; other languages return
    *name* unchanged.
    """
    if not name:
        return name
    prefixes = _FR_ARTICLES if lang == "fr" else _PT_ARTICLES if lang == "pt" else ()
    for prefix in prefixes:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _article_pt(noun_or_meta):
    if isinstance(noun_or_meta, dict):
        article = noun_or_meta.get("article")
        if article is not None:
            return article
        if noun_or_meta.get("plural", False):
            return "as" if noun_or_meta.get("feminine", False) else "os"
        return "a" if noun_or_meta.get("feminine", False) else "o"

    if not noun_or_meta:
        return ""
    lower = noun_or_meta.lower()
    for article in ("os", "as", "o", "a"):
        if lower.startswith(article + " "):
            return article
    return ""


def _noun_name(noun_or_meta):
    if isinstance(noun_or_meta, dict):
        return noun_or_meta.get("name", "")
    return noun_or_meta or ""


def _strip_pt_article(name):
    for prefix in _PT_ARTICLES:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _genitive_pt(noun_or_meta):
    article = _article_pt(noun_or_meta)
    name = _strip_pt_article(_noun_name(noun_or_meta))
    contractions = {
        "o": "do",
        "a": "da",
        "os": "dos",
        "as": "das",
        "": "de",
    }
    prep = contractions.get(article, "de")
    return f"{prep} {name}".strip()


def _preposition_pt(noun_or_meta):
    article = _article_pt(noun_or_meta)
    contractions = {
        "o": "no",
        "a": "na",
        "os": "nos",
        "as": "nas",
        "": "em",
    }
    return contractions.get(article, "em")


def _genitive_fr(noun_or_meta):
    """French genitive: *name* prefixed with the right form of "de".

    Picks the contraction from the noun's gender and number, then applies
    elision:

    * Plural: "des dépenses"           (de + les)
    * Vowel-initial: "de l'éducation"  (elision wins over gender)
    * Feminine singular: "de la santé"
    * Masculine singular: "du Kenya"   (de + le)

    Parameters
    ----------
    noun_or_meta : str or dict
        Either a catalog entry with "name" / "plural" / "feminine" keys,
        or a string with optional article prefix.

    Returns
    -------
    str
        Preposition *and* noun — "du Kenya", "de la santé" — never the bare
        contraction, so callers interpolate the result whole.
    """
    if isinstance(noun_or_meta, dict):
        # Strip any article baked into the name (Portuguese stores "o Togo";
        # French stores bare nouns) so it is not articled twice.
        name = strip_article("fr", noun_or_meta.get("name", ""))
        if not name:
            return "de"
        if noun_or_meta.get("plural", False):
            return f"des {name}"
        if name[0].lower() in _FRENCH_VOWELS:
            return f"de l'{name}"
        if noun_or_meta.get("feminine", False):
            return f"de la {name}"
        return f"du {name}"

    # Legacy: parse article from string
    if not noun_or_meta:
        return "de"
    if noun_or_meta.startswith("les "):
        return "des " + noun_or_meta[4:]
    if noun_or_meta.startswith("le "):
        return "du " + noun_or_meta[3:]
    if noun_or_meta.startswith(("la ", "l'")):
        return "de " + noun_or_meta
    first = noun_or_meta[0].lower()
    if first in _FRENCH_VOWELS:
        return "d'" + noun_or_meta
    return "de " + noun_or_meta


def _preposition_fr(noun_or_meta):
    """Select French preposition for locative context based on noun metadata.

    Determines the correct preposition (en/au/aux) based on noun's gender
    and number properties, following standard French grammar rules:

    * Feminine singular: "en"    (e.g., "en santé", "en France")
    * Masculine singular: "au"   (e.g., "au transport", "au Kenya")
    * Plural: "aux"             (e.g., "aux services", "aux États-Unis")

    Parameters
    ----------
    noun_or_meta : str or dict
        Either a dict with "plural" and "feminine" boolean keys (metadata),
        or a string with article prefix for legacy support.

    Returns
    -------
    str
        The preposition: "en", "au", or "aux".
    """
    if isinstance(noun_or_meta, dict):
        # Metadata-driven selection
        plural = noun_or_meta.get("plural", False)
        feminine = noun_or_meta.get("feminine", False)

        if plural:
            return "aux"
        elif feminine:
            return "en"
        else:
            return "au"

    # Legacy: parse article from string (for backward compatibility)
    if not noun_or_meta:
        return "en"  # safe default
    if noun_or_meta.startswith("les "):
        return "aux"
    elif noun_or_meta.startswith("le "):
        return "au"
    elif noun_or_meta.startswith(("la ", "l'")):
        return "en"
    else:
        return "à"  # no article — use "à"


def elide_que(lang, name):
    """Return the language-appropriate equivalent of "that"/"que".

    French elides "que" to "qu'" before a vowel sound — required in
    templates like "tandis que {name}" where {name} could start with
    any letter (e.g. a region name like "Afar" or "Asmara"):

    * ``elide_que("fr", "Afar")``  → ``"qu'"``
    * ``elide_que("fr", "Kampala")`` → ``"que "``
    * ``elide_que("en", …)`` → ``"that "`` (no elision in English)
    """
    if lang == "fr" and name and name[0].lower() in _FRENCH_VOWELS:
        return "qu'"
    if lang == "fr" or lang == "pt":
        return "que "
    return "that "
    return "que "


def preposition(lang, noun_or_meta, capitalize=False):
    """Return preposition + noun for locative context ('in/at').

    Selects the correct preposition based on noun's grammatical properties
    (gender, number). French uses different prepositions (en/au/aux) depending
    on the noun; English uses "in" uniformly.

    Parameters
    ----------
    lang : str
        Language code ("en", "fr", …).
    noun_or_meta : str or dict
        Noun with grammatical metadata: dict with "name", "plural", and
        "feminine" keys, OR a string with optional article prefix (legacy).
        Examples:
        * {"name": "santé", "plural": False, "feminine": True}
        * {"name": "Kenya", "plural": False, "feminine": False}
        * "le Kenya" (legacy, article-based)
    capitalize : bool, default False
        If True, capitalize the result for sentence-start usage.
        Example: "Au Kenya" (True) vs "au Kenya" (False).

    Returns
    -------
    str
        Preposition + noun: "en santé", "Au Kenya", "in transport", etc.
    """
    if not noun_or_meta:
        return noun_or_meta

    if lang == "fr":
        prep = _preposition_fr(noun_or_meta)
        # Extract noun name from metadata or string
        if isinstance(noun_or_meta, dict):
            noun_name = noun_or_meta.get("name", "")
        else:
            # Legacy: strip article from string
            noun_name = noun_or_meta
            for prefix in ("les ", "le ", "la ", "l'"):
                if noun_name.startswith(prefix):
                    noun_name = noun_name[len(prefix):]
                    break
        result = f"{prep} {noun_name}"
    elif lang == "pt":
        prep = _preposition_pt(noun_or_meta)
        noun_name = _strip_pt_article(_noun_name(noun_or_meta))
        result = f"{prep} {noun_name}"
    elif lang == "en":
        # Extract noun name from metadata or string
        if isinstance(noun_or_meta, dict):
            noun_name = noun_or_meta.get("name", "")
        else:
            noun_name = noun_or_meta
        result = f"in {noun_name}"
    else:
        result = noun_or_meta if isinstance(noun_or_meta, str) else str(noun_or_meta)

    # Capitalize for sentence-start usage
    if capitalize and result:
        result = result[0].upper() + result[1:]

    return result


def genitive(lang, name):
    """Return the genitive ("of X") form of *name* in the given language.

    The genitive role expresses attribution or origin: "of X" in English,
    "de X" (with contractions and elision) in French. Use this when you
    need to interpolate a noun after a "de"/"of" preposition in a template.

    Parameters
    ----------
    lang : str
        Language code ("en", "fr", …).
    name : str or dict
        A catalog entry — ``t(key, lang, meta=True)`` — or a noun phrase.
        Prefer the entry: French and Portuguese pick the contraction from
        its "plural" / "feminine" keys, whereas a bare string can only be
        inflected when it carries its own article ("le taux", "o Togo").

    Returns
    -------
    str
        Preposition *and* noun, ready to interpolate whole — every language
        returns the full phrase, never a dangling contraction:

        * French: article contractions (de+le→du, de+les→des) and vowel
          elision (de l'éducation vs. de la santé).
        * Portuguese: de+o→do, de+a→da, de+os→dos, de+as→das.
        * English: prepends "of ".
        * Other: returns *name* unchanged.
    """
    if not name:
        return name
    if lang == "fr":
        return _genitive_fr(name)
    if lang == "pt":
        return _genitive_pt(name)
    if lang == "en":
        return "of " + _noun_name(name)
    return _noun_name(name) if isinstance(name, dict) else name
