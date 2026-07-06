"""Language fallback helpers for the external trend-narrative package."""

from trend_narrative import get_relationship_narrative, get_segment_narrative


PORTUGUESE_TREND_LANGUAGE_CODES = ("pt", "ptbr")


def _is_unsupported_language_error(exc, attempted_lang):
    if isinstance(exc, KeyError) and exc.args and exc.args[0] == attempted_lang:
        return True
    message = str(exc).lower()
    return (
        attempted_lang.lower() in message
        and any(token in message for token in ("lang", "language", "support", "unsupported"))
    )


def _call_with_language_fallback(func, lang, fallback_kwargs=None, **kwargs):
    """Try Portuguese trend-narrative support before falling back to English."""
    if lang == "pt":
        last_language_error = None
        for candidate in PORTUGUESE_TREND_LANGUAGE_CODES:
            try:
                return func(**kwargs, lang=candidate)
            except Exception as exc:
                if _is_unsupported_language_error(exc, candidate):
                    last_language_error = exc
                    continue
                raise

        if last_language_error is not None:
            call_kwargs = {**kwargs, **(fallback_kwargs or {}), "lang": "en"}
            return func(**call_kwargs)

    return func(**kwargs, lang=lang)


def get_segment_narrative_i18n(*, lang="en", fallback_kwargs=None, **kwargs):
    return _call_with_language_fallback(
        get_segment_narrative, lang, fallback_kwargs=fallback_kwargs, **kwargs
    )


def get_relationship_narrative_i18n(*, lang="en", fallback_kwargs=None, **kwargs):
    return _call_with_language_fallback(
        get_relationship_narrative, lang, fallback_kwargs=fallback_kwargs, **kwargs
    )
