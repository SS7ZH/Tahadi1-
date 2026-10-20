"""Consistent Arabic error responses: {"detail": "...", "code": "..."}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("tahadi")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, detail: str, headers: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.headers = headers


def not_found(detail: str = "العنصر المطلوب غير موجود") -> AppError:
    return AppError(404, "NOT_FOUND", detail)


def forbidden(detail: str = "ليس لديك صلاحية للقيام بهذا الإجراء") -> AppError:
    return AppError(403, "FORBIDDEN", detail)


def bad_request(detail: str, code: str = "BAD_REQUEST") -> AppError:
    return AppError(400, code, detail)


def unprocessable(detail: str, code: str = "VALIDATION_ERROR") -> AppError:
    return AppError(422, code, detail)


_HTTP_DEFAULTS = {
    400: ("BAD_REQUEST", "طلب غير صالح"),
    401: ("NOT_AUTHENTICATED", "يجب تسجيل الدخول"),
    403: ("FORBIDDEN", "ليس لديك صلاحية للقيام بهذا الإجراء"),
    404: ("NOT_FOUND", "المسار المطلوب غير موجود"),
    405: ("METHOD_NOT_ALLOWED", "الطريقة غير مسموحة لهذا المسار"),
    409: ("CONFLICT", "تعارض في البيانات"),
    429: ("RATE_LIMITED", "محاولات كثيرة، حاول لاحقاً"),
}

FIELD_LABELS = {
    "email": "البريد الإلكتروني",
    "password": "كلمة المرور",
    "new_password": "كلمة المرور الجديدة",
    "current_password": "كلمة المرور الحالية",
    "full_name": "الاسم",
    "phone": "رقم الجوال",
    "role": "الدور",
    "sex": "الجنس",
    "birth_date": "تاريخ الميلاد",
    "height_cm": "الطول",
    "goal": "الهدف",
    "activity_key": "مستوى النشاط",
    "session_date": "تاريخ القياس",
    "body": "النص",
    "age": "العمر",
    "weight": "الوزن",
    "height": "الطول",
    "status": "الحالة",
    "factor": "المعامل",
    "key": "المفتاح",
    "name_ar": "الاسم بالعربية",
    "trainer_id": "المدرب",
}


def _validation_message(errors: list[dict]) -> str:
    if not errors:
        return "البيانات المرسلة غير صالحة"
    err = errors[0]
    loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
    field = loc[-1] if loc else ""
    label = FIELD_LABELS.get(field, field)
    etype = err.get("type", "")
    msg = str(err.get("msg", ""))
    if etype == "value_error" and msg.startswith("Value error, "):
        return msg.removeprefix("Value error, ")
    if etype == "missing":
        return f"الحقل مطلوب: {label}"
    if field == "email" or "email" in msg.lower():
        return "البريد الإلكتروني غير صالح"
    if etype == "string_too_short":
        min_len = err.get("ctx", {}).get("min_length")
        return f"«{label}» قصير جداً (الحد الأدنى {min_len} أحرف)"
    if etype == "string_too_long":
        return f"«{label}» أطول من المسموح"
    if etype in ("greater_than_equal", "greater_than", "less_than_equal", "less_than"):
        return f"قيمة «{label}» خارج النطاق المسموح"
    if etype == "literal_error" or etype == "enum":
        return f"قيمة «{label}» غير مسموحة"
    if etype.startswith("date") or etype.startswith("datetime"):
        return f"تاريخ غير صالح في «{label}»"
    return f"قيمة غير صالحة في «{label}»" if label else "البيانات المرسلة غير صالحة"


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
        code, default = _HTTP_DEFAULTS.get(exc.status_code, ("ERROR", "حدث خطأ"))
        detail = exc.detail if isinstance(exc.detail, str) and not exc.detail.isascii() else default
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
            content={"detail": "حدث خطأ غير متوقع في الخادم", "code": "INTERNAL_ERROR"},
        )
