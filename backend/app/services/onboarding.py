"""Subscriptions, health declarations, versioned templates, signing, and the client onboarding status."""
import calendar
import re
from datetime import date, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found, unprocessable
from app.core.i18n import get_language, tr
from app.core.rate_limit import client_ip
from app.models import (
    DocumentTemplate,
    HealthDeclaration,
    MedicalFile,
    SignedDocument,
    Subscription,
    SubscriptionPlan,
    User,
)

# ---------------- dates ----------------


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def end_date_for(start: date, months: int) -> date:
    """1 month from 2026-10-22 ends on 2026-11-21 (inclusive)."""
    return add_months(start, months) - timedelta(days=1)


def days_left(sub: Subscription | None, today: date | None = None) -> int | None:
    if sub is None:
        return None
    return (sub.end_date - (today or date.today())).days


def subscription_status(sub: Subscription | None, today: date | None = None) -> str | None:
    if sub is None:
        return None
    today = today or date.today()
    if sub.start_date > today:
        return "upcoming"
    if sub.end_date < today:
        return "expired"
    return "active"


# ---------------- lookups ----------------


def latest_subscription(db: Session, client_id: int) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .where(Subscription.client_id == client_id)
        .order_by(Subscription.created_at.desc(), Subscription.id.desc())
        .limit(1)
    )


def current_declaration(db: Session, client_id: int) -> HealthDeclaration | None:
    return db.scalar(
        select(HealthDeclaration)
        .where(HealthDeclaration.client_id == client_id)
        .order_by(HealthDeclaration.created_at.desc(), HealthDeclaration.id.desc())
        .limit(1)
    )


def active_template(db: Session, kind: str) -> DocumentTemplate:
    t = db.scalar(
        select(DocumentTemplate)
        .where(DocumentTemplate.kind == kind, DocumentTemplate.is_active.is_(True))
        .order_by(DocumentTemplate.version.desc())
        .limit(1)
    )
    if t is None:
        raise AppError(503, "TEMPLATE_MISSING", tr("لا يوجد نموذج مفعّل", "No active template"))
    return t


def has_signed(db: Session, client_id: int, kind: str, subscription_id: int | None = None) -> bool:
    stmt = select(SignedDocument.id).where(SignedDocument.client_id == client_id, SignedDocument.kind == kind)
    if subscription_id is not None:
        stmt = stmt.where(SignedDocument.subscription_id == subscription_id)
    return db.scalar(stmt.limit(1)) is not None


def status(db: Session, client: User) -> dict:
    """Onboarding progress, computed from data so a renewal (new subscription) asks for a new contract."""
    sub = latest_subscription(db, client.id)
    decl = current_declaration(db, client.id)
    step1 = sub is not None
    step2 = decl is not None and has_signed(db, client.id, "disclaimer")
    step3 = step1 and has_signed(db, client.id, "contract", sub.id)
    step = 1 if not step1 else 2 if not step2 else 3 if not step3 else None
    return {
        "complete": step is None,
        "step": step,
        "steps": {"subscription": step1, "health": step2, "contract": step3},
        "subscription": subscription_out(sub) if sub else None,
    }


def is_onboarded(db: Session, client: User) -> bool:
    return status(db, client)["complete"]


# ---------------- serialization ----------------


def plan_out(p: SubscriptionPlan) -> dict:
    return {
        "id": p.id,
        "name_ar": p.name_ar,
        "name_en": p.name_en,
        "months": p.months,
        "price": float(p.price) if p.price is not None else None,
        "currency": p.currency,
        "is_active": p.is_active,
        "sort_order": p.sort_order,
    }


def subscription_out(s: Subscription) -> dict:
    return {
        "id": s.id,
        "client_id": s.client_id,
        "plan_id": s.plan_id,
        "plan_name_ar": s.plan_name_ar,
        "plan_name_en": s.plan_name_en,
        "months": s.months,
        "price": float(s.price) if s.price is not None else None,
        "currency": s.currency,
        "start_date": s.start_date,
        "end_date": s.end_date,
        "kind": s.kind,
        "status": subscription_status(s),
        "days_left": days_left(s),
        "contract_signed": None,  # filled by callers that need it
        "created_at": s.created_at,
    }


def file_out(f: MedicalFile) -> dict:
    return {
        "id": f.id,
        "declaration_id": f.declaration_id,
        "original_name": f.original_name,
        "content_type": f.content_type,
        "size_bytes": f.size_bytes,
        "uploaded_at": f.uploaded_at,
    }


def declaration_out(d: HealthDeclaration) -> dict:
    return {
        "id": d.id,
        "has_chronic": d.has_chronic,
        "conditions": d.conditions or [],
        "details": d.details,
        "medications": d.medications,
        "injuries": d.injuries,
        "created_at": d.created_at,
        "reviewed_at": d.reviewed_at,
        "files": [file_out(f) for f in d.files],
    }


def signed_out(s: SignedDocument) -> dict:
    return {
        "id": s.id,
        "client_id": s.client_id,
        "kind": s.kind,
        "template_version": s.template_version,
        "language": s.language,
        "rendered_text": s.rendered_text,
        "typed_name": s.typed_name,
        "signed_at": s.signed_at,
        "ip_address": s.ip_address,
        "subscription_id": s.subscription_id,
        "health_declaration_id": s.health_declaration_id,
        "details": s.details or {},
    }


def template_out(t: DocumentTemplate) -> dict:
    return {
        "id": t.id,
        "kind": t.kind,
        "version": t.version,
        "body_ar": t.body_ar,
        "body_en": t.body_en,
        "is_active": t.is_active,
        "created_at": t.created_at,
        "created_by_name": t.created_by.full_name if t.created_by else None,
    }


# ---------------- templates ----------------


class _SafeDict(dict):
    def __missing__(self, key):  # unknown {placeholders} are left as they are
        return "{" + key + "}"


def template_context(client: User, sub: Subscription | None, lang: str) -> dict:
    p = client.profile
    coach = p.trainer.full_name if p and p.trainer else "—"
    dash = "—"
    if sub is not None and sub.price is not None:
        price = f"{float(sub.price):,.2f} {sub.currency}"
    else:
        price = "غير محدد" if lang == "ar" else "Not specified"
    return {
        "client_name": client.full_name,
        "coach_name": coach,
        "plan": (sub.plan_name_ar if lang == "ar" else sub.plan_name_en) if sub else dash,
        "start_date": sub.start_date.isoformat() if sub else dash,
        "end_date": sub.end_date.isoformat() if sub else dash,
        "price": price,
        "today": date.today().isoformat(),
    }


def render(body: str, ctx: dict) -> str:
    return body.format_map(_SafeDict(ctx))


def rendered_template(db: Session, client: User, kind: str, lang: str | None = None) -> dict:
    lang = lang or get_language()
    t = active_template(db, kind)
    sub = latest_subscription(db, client.id)
    body = t.body_en if lang == "en" else t.body_ar
    return {"template_id": t.id, "version": t.version, "language": lang, "text": render(body, template_context(client, sub, lang))}


# ---------------- signing ----------------

_TASHKEEL = re.compile(r"[ً-ْـ]")  # Arabic diacritics + tatweel


def normalize_name(name: str) -> str:
    name = _TASHKEEL.sub("", name or "")
    name = name.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
    return " ".join(name.split()).casefold()


def check_signature(client: User, typed_name: str, agreed: bool) -> str:
    if not agreed:
        raise unprocessable(tr("يجب الموافقة قبل التوقيع", "You must agree before signing"), "NOT_AGREED")
    typed = " ".join((typed_name or "").split())
    if normalize_name(typed) != normalize_name(client.full_name):
        raise unprocessable(
            tr(f"اكتب اسمك الكامل كما هو مسجل: {client.full_name}", f"Type your full name exactly as registered: {client.full_name}"),
            "NAME_MISMATCH",
        )
    return typed


def sign(
    db: Session,
    client: User,
    *,
    kind: str,
    template_id: int,
    typed_name: str,
    request: Request,
    subscription: Subscription | None = None,
    declaration: HealthDeclaration | None = None,
) -> SignedDocument:
    lang = get_language()
    t = active_template(db, kind)
    if t.id != template_id:
        # The template changed after the page was opened: the client must read the new text.
        raise AppError(409, "TEMPLATE_CHANGED", tr("تم تحديث النص، يرجى قراءته مرة أخرى", "The text was updated, please read it again"))
    ctx = template_context(client, subscription, lang)
    doc = SignedDocument(
        client_id=client.id,
        kind=kind,
        template_id=t.id,
        template_version=t.version,
        language=lang,
        rendered_text=render(t.body_en if lang == "en" else t.body_ar, ctx),
        typed_name=typed_name,
        ip_address=client_ip(request)[:64],
        user_agent=(request.headers.get("user-agent") or "")[:400],
        subscription_id=subscription.id if subscription else None,
        health_declaration_id=declaration.id if declaration else None,
        details={k: ctx[k] for k in ("client_name", "coach_name", "plan", "start_date", "end_date", "price")},
    )
    db.add(doc)
    return doc


# ---------------- subscriptions ----------------


def get_plan(db: Session, plan_id: int, *, active_only: bool = True) -> SubscriptionPlan:
    plan = db.get(SubscriptionPlan, plan_id)
    if plan is None or (active_only and not plan.is_active):
        raise not_found(tr("الخطة غير موجودة", "Plan not found"))
    return plan


def create_subscription(db: Session, actor: User, client: User, plan: SubscriptionPlan, start: date, kind: str) -> Subscription:
    sub = Subscription(
        client_id=client.id,
        plan_id=plan.id,
        plan_name_ar=plan.name_ar,
        plan_name_en=plan.name_en,
        months=plan.months,
        price=plan.price,
        currency=plan.currency,
        start_date=start,
        end_date=end_date_for(start, plan.months),
        kind=kind,
        created_by_id=actor.id,
    )
    db.add(sub)
    return sub
