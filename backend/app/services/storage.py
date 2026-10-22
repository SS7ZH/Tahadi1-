"""Private file storage.

Production: Supabase Storage, private bucket. Uploads go through the backend with the secret key;
viewing returns a signed URL that expires after SIGNED_URL_SECONDS (5 minutes). No public URLs.
Development/tests: files on local disk, served through a short-lived HMAC-signed backend URL.
"""
import hashlib
import hmac
import time
import uuid
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.errors import AppError, unprocessable
from app.core.i18n import tr

MAX_BYTES = 10 * 1024 * 1024
MAX_FILES = 3

# File type by content (magic bytes), never by extension alone.
SIGNATURES = (
    (b"%PDF-", "application/pdf", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
)


def sniff(data: bytes) -> tuple[str, str]:
    for magic, mime, ext in SIGNATURES:
        if data.startswith(magic):
            return mime, ext
    raise unprocessable(tr("نوع الملف غير مسموح؛ المسموح PDF أو JPG أو PNG", "File type not allowed; use PDF, JPG or PNG"), "FILE_TYPE")


def check_size(size: int) -> None:
    if size > MAX_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", tr("حجم الملف يتجاوز 10 ميجابايت", "The file is larger than 10 MB"))
    if size == 0:
        raise unprocessable(tr("الملف فارغ", "The file is empty"), "FILE_EMPTY")


def new_path(client_id: int, ext: str) -> str:
    return f"clients/{client_id}/{uuid.uuid4().hex}.{ext}"


# ---------------- local (dev/tests) ----------------
def _local_root() -> Path:
    root = Path(settings.UPLOAD_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _local_file(path: str) -> Path:
    target = (_local_root() / path).resolve()
    if _local_root() not in target.parents:
        raise AppError(400, "BAD_PATH", "bad path")
    return target


def local_token(path: str, expires: int) -> str:
    msg = f"{path}|{expires}".encode()
    return hmac.new(settings.JWT_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def local_read(path: str, expires: int, token: str) -> bytes:
    if expires < time.time() or not hmac.compare_digest(local_token(path, expires), token):
        raise AppError(403, "LINK_EXPIRED", tr("انتهت صلاحية الرابط", "This link has expired"))
    return _local_file(path).read_bytes()


# ---------------- Supabase ----------------
def _headers() -> dict:
    key = settings.SUPABASE_SECRET_KEY or ""
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _base() -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1"


def save(path: str, data: bytes, content_type: str) -> None:
    if settings.remote_storage:
        r = httpx.post(
            f"{_base()}/object/{settings.SUPABASE_STORAGE_BUCKET}/{quote(path)}",
            content=data,
            headers={**_headers(), "Content-Type": content_type, "x-upsert": "false"},
            timeout=60,
        )
        if r.status_code >= 300:
            raise AppError(502, "STORAGE_ERROR", tr("تعذر حفظ الملف، حاول مرة أخرى", "Could not store the file, try again"))
        return
    if settings.is_production:
        # Render's disk is ephemeral: never silently keep health files on it.
        raise AppError(503, "STORAGE_NOT_CONFIGURED", tr("تخزين الملفات غير مهيأ", "File storage is not configured"))
    target = _local_file(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def signed_url(path: str, api_base: str) -> str:
    seconds = settings.SIGNED_URL_SECONDS
    if settings.remote_storage:
        r = httpx.post(
            f"{_base()}/object/sign/{settings.SUPABASE_STORAGE_BUCKET}/{quote(path)}",
            json={"expiresIn": seconds},
            headers=_headers(),
            timeout=30,
        )
        if r.status_code >= 300:
            raise AppError(502, "STORAGE_ERROR", tr("تعذر فتح الملف، حاول مرة أخرى", "Could not open the file, try again"))
        signed = r.json().get("signedURL") or r.json().get("signedUrl")
        return f"{_base()}{signed}" if signed.startswith("/") else signed
    expires = int(time.time()) + seconds
    return f"{api_base}/files/local?path={quote(path)}&expires={expires}&token={local_token(path, expires)}"
