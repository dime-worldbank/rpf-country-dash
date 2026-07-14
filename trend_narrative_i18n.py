"""Language fallback helpers for the external trend-narrative package."""

from trend_narrative import get_relationship_narrative, get_segment_narrative


def _is_unsupported_language_error(exc, attempted_lang):
    return (
        isinstance(exc, ValueError)
        and str(exc).startswith(f"Unsupported language '{attempted_lang}'.")
    )


def _call_with_language_fallback(func, lang, **kwargs):
    """Try the requested language, then English if it is unsupported."""
    if lang == "en":
        return func(**kwargs, lang=lang)

    try:
        return func(**kwargs, lang=lang)
    except Exception as exc:
        if not _is_unsupported_language_error(exc, lang):
            raise

        return func(**kwargs, lang="en")


def get_segment_narrative_i18n(*, lang="en", **kwargs):
    return _call_with_language_fallback(get_segment_narrative, lang, **kwargs)


def get_relationship_narrative_i18n(*, lang="en", **kwargs):
    return _call_with_language_fallback(get_relationship_narrative, lang, **kwargs)
