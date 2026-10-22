"""Consistent localized error responses: {"detail": "...", "code": "..."} (Arabic default, English via Accept-Language)."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.i18n import tr

logger = logging.getLogger("tahadi")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, detail: str, headers: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.headers = headers


def not_found(detail: str | None = None) -> AppError:
    return AppError(404, "NOT_FOUND", detail or tr("العنصر المطلوب غير موجود", "The requested item was not found"))


def forbidden(detail: str | None = None) -> AppError:
    return AppError(403, "FORBIDDEN", detail or tr("ليس لديك صلاحية للقيام بهذا الإجراء", "You do not have permission to do this"))


def bad_request(detail: str, code: str = "BAD_REQUEST") -> AppError:
    return AppError(400, code, detail)


def unprocessable(detail: str, code: str = "VALIDATION_ERROR") -> AppError:
    return AppError(422, code, detail)


_HTTP_DEFAULTS = {
    400: ("BAD_REQUEST", "طلب غير صالح", "Invalid request"),
    401: ("NOT_AUTHENTICATED", "يجب تسجيل الدخول", "You need to log in"),
    403: ("FORBIDDEN", "ليس لديك صلاحية للقيام بهذا الإجراء", "You do not have permission to do this"),
    404: ("NOT_FOUND", "المسار المطلوب غير موجود", "The requested path was not found"),
    405: ("METHOD_NOT_ALLOWED", "الطريقة غير مسموحة لهذا المسار", "Method not allowed for this path"),
    409: ("CONFLICT", "تعارض في البيانات", "Data conflict"),
    413: ("TOO_LARGE", "حجم الطلب كبير جداً", "Request is too large"),
    429: ("RATE_LIMITED", "محاولات كثيرة، حاول لاحقاً", "Too many attempts, try again later"),
}

FIELD_LABELS = {
    "email": ("البريد الإلكتروني", "Email"),
    "password": ("كلمة المرور", "Password"),
    "new_password": ("كلمة المرور الجديدة", "New password"),
    "current_password": ("كلمة المرور الحالية", "Current password"),
    "full_name": ("الاسم", "Name"),
    "phone": ("رقم الجوال", "Phone"),
    "role": ("الدور", "Role"),
    "sex": ("الجنس", "Sex"),
    "birth_date": ("تاريخ الميلاد", "Birth date"),
    "height_cm": ("الطول", "Height"),
    "goal": ("الهدف", "Goal"),
    "activity_key": ("مستوى النشاط", "Activity level"),
    "session_date": ("تاريخ القياس", "Measurement date"),
    "body": ("النص", "Text"),
    "age": ("العمر", "Age"),
    "weight": ("الوزن", "Weight"),
    "height": ("الطول", "Height"),
    "status": ("الحالة", "Status"),
    "factor": ("المعامل", "Factor"),
    "key": ("المفتاح", "Key"),
    "name_ar": ("الاسم بالعربية", "Arabic name"),
    "name_en": ("الاسم بالإنجليزية", "English name"),
    "trainer_id": ("المدرب", "Coach"),
    "title": ("العنوان", "Title"),
    "start_date": ("تاريخ البداية", "Start date"),
    "typed_name": ("الاسم الكامل", "Full name"),
    "meals_per_day": ("عدد الوجبات", "Meals per day"),
    "calories": ("السعرات", "Calories"),
}


def _label(field: str) -> str:
    pair = FIELD_LABELS.get(field)
    return tr(*pair) if pair else field


def _validation_message(errors: list[dict]) -> str:
    invalid = tr("البيانات المرسلة غير صالحة", "The submitted data is invalid")
    if not errors:
        return invalid
    err = errors[0]
    loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
    field = loc[-1] if loc else ""
    label = _label(field)
    etype = err.get("type", "")
    msg = str(err.get("msg", ""))
    if etype == "value_error" and msg.startswith("Value error, "):
        return msg.removeprefix("Value error, ")
    if etype == "missing":
        return tr(f"الحقل مطلوب: {label}", f"Required field: {label}")
    if field == "email" or "email" in msg.lower():
        return tr("البريد الإلكتروني غير صالح", "Invalid email address")
    if etype == "string_too_short":
        n = err.get("ctx", {}).get("min_length")
        return tr(f"«{label}» قصير جداً (الحد الأدنى {n} أحرف)", f"“{label}” is too short (minimum {n} characters)")
    if etype == "string_too_long":
        return tr(f"«{label}» أطول من المسموح", f"“{label}” is too long")
    if etype in ("greater_than_equal", "greater_than", "less_than_equal", "less_than"):
        return tr(f"قيمة «{label}» خارج النطاق المسموح", f"“{label}” is out of the allowed range")
    if etype in ("literal_error", "enum"):
        return tr(f"قيمة «{label}» غير مسموحة", f"“{label}” has a value that is not allowed")
    if etype.startswith("date") or etype.startswith("datetime"):
        return tr(f"تاريخ غير صالح في «{label}»", f"Invalid date in “{label}”")
    if etype == "extra_forbidden":
        return tr(f"لا يمكن تعديل «{label}»", f"“{label}” cannot be changed")
    if label:
        return tr(f"قيمة غير صالحة في «{label}»", f"Invalid value in “{label}”")
    return invalid


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code, ar, en = _HTTP_DEFAULTS.get(exc.status_code, ("ERROR", "حدث خطأ", "An error occurred"))
        detail = tr(ar, en)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail, "code": code},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        return JSONResponse(
            status_code=422,
            content={
                "detail": _validation_message(errors),
                "code": "VALIDATION_ERROR",
                "fields": [".".join(str(p) for p in e.get("loc", [])) for e in errors],
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": tr("حدث خطأ غير متوقع في الخادم", "Unexpected server error"), "code": "INTERNAL_ERROR"},
        )
