"""HTML (Jinja2) → PDF (WeasyPrint). Fonts are bundled and loaded with @font-face."""
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import AppError
from app.core.i18n import get_language, tr
from app.pdf.labels import LABELS

PDF_DIR = Path(__file__).resolve().parent
_env = Environment(loader=FileSystemLoader(PDF_DIR / "templates"), autoescape=select_autoescape(["html"]))


def _num(v, digits: int = 1) -> str:
    if v is None:
        return "—"
    v = float(v)
    if v.is_integer() or digits == 0:
        return f"{round(v):,}"
    return f"{v:,.{digits}f}".rstrip("0").rstrip(".")


_env.filters["num"] = _num


def render_html(template: str, *, title_key: str, coach_name: str | None, client_name: str | None, **ctx) -> str:
    lang = get_language()
    L = LABELS[lang]
    return _env.get_template(template).render(
        L=L,
        lang=lang,
        dir="rtl" if lang == "ar" else "ltr",
        title=L["titles"][title_key],
        coach_name=coach_name or "—",
        client_name=client_name or "—",
        exported=date.today().isoformat(),
        **ctx,
    )


def html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML  # imported lazily: needs Pango (installed in the Docker image)
    except OSError as e:  # pragma: no cover - only on machines without Pango
        raise AppError(
            503, "PDF_UNAVAILABLE", tr("توليد ملفات PDF غير متاح على هذا الخادم", "PDF generation is not available on this server")
        ) from e
    return HTML(string=html, base_url=str(PDF_DIR) + "/").write_pdf()


_UNSAFE = re.compile(r"[\\/:*?\"<>|\x00-\x1f]+")


def filename(document: str, client_name: str | None) -> str:
    name = _UNSAFE.sub("", (client_name or "").strip())
    name = re.sub(r"\s+", "-", name) or "tahadi"
    return f"tahadi_{document}_{name}_{date.today().isoformat()}.pdf"


def content_disposition(fname: str) -> str:
    """Arabic-safe: ASCII fallback + RFC 5987 filename*."""
    ascii_name = fname.encode("ascii", "ignore").decode() or "tahadi.pdf"
    ascii_name = re.sub(r"_+", "_", ascii_name.replace("-_", "_"))
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(fname)}"
