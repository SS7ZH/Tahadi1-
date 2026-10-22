"""Per-request language (Arabic default, English optional) chosen from the Accept-Language header."""
from contextvars import ContextVar

SUPPORTED = ("ar", "en")
DEFAULT = "ar"

_lang: ContextVar[str] = ContextVar("lang", default=DEFAULT)


def parse_accept_language(header: str | None) -> str:
    """Return 'en' or 'ar' from an Accept-Language header (first supported tag wins)."""
    if not header:
        return DEFAULT
    for part in header.split(","):
        tag = part.split(";")[0].strip().lower()
        base = tag.split("-")[0]
        if base in SUPPORTED:
            return base
    return DEFAULT


def get_language() -> str:
    return _lang.get()


def set_language(lang: str):
    """Returns a token for ContextVar.reset()."""
    return _lang.set(lang if lang in SUPPORTED else DEFAULT)


def tr(ar: str, en: str) -> str:
    """Pick the message for the current request language."""
    return en if _lang.get() == "en" else ar


def pick(ar: str | None, en: str | None) -> str | None:
    """Pick a localized DB field, falling back to Arabic when English is missing."""
    return (en or ar) if _lang.get() == "en" else (ar or en)


class LanguageMiddleware:
    """Pure ASGI middleware so the ContextVar is visible to the endpoint and its threadpool."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        header = None
        for k, v in scope.get("headers", []):
            if k == b"accept-language":
                header = v.decode("latin-1")
                break
        # ?lang= (used by PDF download links) overrides the header
        qs = scope.get("query_string", b"").decode("latin-1")
        for pair in qs.split("&"):
            if pair.startswith("lang="):
                header = pair[5:]
        token = set_language(parse_accept_language(header))
        try:
            await self.app(scope, receive, send)
        finally:
            _lang.reset(token)
