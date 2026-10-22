"""Coach/admin side of subscriptions, health declarations, medical files and signed documents;
admin plans & templates; public plan list; signed file links."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_accessible_client, get_current_user, require_role
from app.core.errors import bad_request, not_found
from app.core.i18n import tr
from app.db.reference_data import TEMPLATE_PLACEHOLDERS
from app.db.session import get_db
from app.models import (
    DocumentTemplate,
    HealthDeclaration,
    MedicalFile,
    SignedDocument,
    Subscription,
    SubscriptionPlan,
    User,
)
from app.schemas.onboarding import PlanIn, PlanUpdate, SubscriptionCreateIn, SubscriptionUpdateIn, TemplateIn
from app.services import audit, permissions, storage
from app.services import onboarding as svc

router = APIRouter(tags=["documents"])
staff = require_role("trainer", "admin")
admin_only = require_role("admin")


# ---------------- subscriptions ----------------
@router.get("/clients/{client_id}/subscriptions")
def list_subscriptions(client: User = Depends(get_accessible_client), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Subscription).where(Subscription.client_id == client.id).order_by(Subscription.created_at.desc(), Subscription.id.desc())
    ).all()
    signed = set(
        db.scalars(select(SignedDocument.subscription_id).where(SignedDocument.client_id == client.id, SignedDocument.kind == "contract"))
    )
    out = []
    for s in rows:
        item = svc.subscription_out(s)
        item["contract_signed"] = s.id in signed
        out.append(item)
    return {"current": out[0] if out else None, "history": out}


@router.post("/clients/{client_id}/subscriptions", status_code=status.HTTP_201_CREATED)
def renew_subscription(client_id: int, data: SubscriptionCreateIn, actor: User = Depends(staff), db: Session = Depends(get_db)):
    """Renew or change plan → the client must sign a new contract at their next login."""
    client = permissions.get_accessible_client(db, actor, client_id)
    plan = svc.get_plan(db, data.plan_id)
    sub = svc.create_subscription(db, actor, client, plan, data.start_date, data.kind)
    db.flush()
    audit.record(db, actor, "create", "subscription", sub.id, {"client_id": client.id, "client_name": client.full_name, "kind": data.kind})
    db.commit()
    return svc.subscription_out(sub)


@router.patch("/subscriptions/{subscription_id}")
def update_subscription(subscription_id: int, data: SubscriptionUpdateIn, actor: User = Depends(staff), db: Session = Depends(get_db)):
    """Change dates or extend; no new contract is needed."""
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise not_found(tr("الاشتراك غير موجود", "Subscription not found"))
    client = permissions.get_accessible_client(db, actor, sub.client_id)
    before = {"start_date": sub.start_date.isoformat(), "end_date": sub.end_date.isoformat()}
    if data.start_date is not None:
        sub.start_date = data.start_date
    if data.end_date is not None:
        sub.end_date = data.end_date
    if sub.end_date < sub.start_date:
        db.rollback()
        raise bad_request(tr("تاريخ النهاية قبل تاريخ البداية", "The end date is before the start date"), "INVALID_RANGE")
    audit.record(
        db, actor, "update", "subscription", sub.id,
        {"client_id": client.id, "client_name": client.full_name, "before": before, "after": {"start_date": sub.start_date.isoformat(), "end_date": sub.end_date.isoformat()}},
    )
    db.commit()
    return svc.subscription_out(sub)


# ---------------- health declaration & files ----------------
@router.get("/clients/{client_id}/health")
def get_health(client: User = Depends(get_accessible_client), db: Session = Depends(get_db)):
    """Client themselves, their coach, admin only (others get 404 from get_accessible_client)."""
    rows = db.scalars(
        select(HealthDeclaration).where(HealthDeclaration.client_id == client.id).order_by(HealthDeclaration.created_at.desc(), HealthDeclaration.id.desc())
    ).all()
    current = rows[0] if rows else None
    return {
        "current": svc.declaration_out(current) if current else None,
        "history": [svc.declaration_out(r) for r in rows],
        "needs_review": bool(current and current.reviewed_at is None and len(rows) > 1),
    }


@router.post("/clients/{client_id}/health/review")
def review_health(client_id: int, actor: User = Depends(staff), db: Session = Depends(get_db)):
    client = permissions.get_accessible_client(db, actor, client_id)
    current = svc.current_declaration(db, client.id)
    if current and current.reviewed_at is None:
        current.reviewed_at = datetime.now(timezone.utc)
        current.reviewed_by_id = actor.id
        db.commit()
    return {"ok": True}


@router.get("/files/{file_id}/url")
def file_url(file_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Short-lived signed link (5 min). Permission is checked first; another coach gets 404."""
    f = db.get(MedicalFile, file_id)
    if f is None:
        raise not_found(tr("الملف غير موجود", "File not found"))
    client = db.get(User, f.client_id)
    if client is None or not permissions.can_access_client(user, client):
        raise not_found(tr("الملف غير موجود", "File not found"))
    audit.record(db, user, "view", "medical_file", f.id, {"client_id": client.id, "client_name": client.full_name})
    db.commit()
    api_base = str(request.base_url).rstrip("/") + "/api/v1"
    return {"url": storage.signed_url(f.storage_path, api_base), "expires_in": settings.SIGNED_URL_SECONDS, "content_type": f.content_type, "name": f.original_name}


@router.get("/files/local", include_in_schema=False)
def local_file(path: str, expires: int, token: str, db: Session = Depends(get_db)):
    """Development/tests only: serves a file from UPLOAD_DIR behind the HMAC token above."""
    if settings.remote_storage or settings.is_production:
        raise not_found()
    row = db.scalar(select(MedicalFile).where(MedicalFile.storage_path == path))
    if row is None:
        raise not_found()
    data = storage.local_read(path, expires, token)
    return Response(content=data, media_type=row.content_type, headers={"Cache-Control": "no-store"})


# ---------------- signed documents (read-only) ----------------
@router.get("/clients/{client_id}/documents")
def list_documents(client: User = Depends(get_accessible_client), db: Session = Depends(get_db)):
    rows = db.scalars(select(SignedDocument).where(SignedDocument.client_id == client.id).order_by(SignedDocument.signed_at.desc())).all()
    return [svc.signed_out(r) for r in rows]


@router.get("/documents/{document_id}")
def get_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(SignedDocument, document_id)
    client = db.get(User, doc.client_id) if doc else None
    if doc is None or client is None or not permissions.can_access_client(user, client):
        raise not_found(tr("المستند غير موجود", "Document not found"))
    return svc.signed_out(doc)


# ---------------- plans ----------------
@router.get("/public/plans")
def public_plans(db: Session = Depends(get_db)):
    rows = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.sort_order)).all()
    return [svc.plan_out(p) for p in rows]


@router.get("/plans")
def plans_for_staff(_: User = Depends(staff), db: Session = Depends(get_db)):
    rows = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.sort_order)).all()
    return [svc.plan_out(p) for p in rows]


@router.get("/admin/plans")
def admin_plans(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    return [svc.plan_out(p) for p in db.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order)).all()]


@router.post("/admin/plans", status_code=status.HTTP_201_CREATED)
def create_plan(data: PlanIn, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    plan = SubscriptionPlan(**data.model_dump(), is_active=True)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return svc.plan_out(plan)


@router.patch("/admin/plans/{plan_id}")
def update_plan(plan_id: int, data: PlanUpdate, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    plan = db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise not_found(tr("الخطة غير موجودة", "Plan not found"))
    changes = data.model_dump(exclude_unset=True, exclude={"clear_price"})
    for field, value in changes.items():
        if value is not None:
            setattr(plan, field, value)
    if data.clear_price:
        plan.price = None
    db.commit()
    db.refresh(plan)
    return svc.plan_out(plan)


# ---------------- templates (versioned) ----------------
@router.get("/admin/templates")
def list_templates(kind: str = Query(pattern="^(contract|disclaimer)$"), _: User = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(DocumentTemplate).where(DocumentTemplate.kind == kind).order_by(DocumentTemplate.version.desc())).unique()
    return {"placeholders": list(TEMPLATE_PLACEHOLDERS), "versions": [svc.template_out(t) for t in rows]}


@router.post("/admin/templates", status_code=status.HTTP_201_CREATED)
def new_template_version(data: TemplateIn, actor: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Editing never changes existing versions (or anything already signed): it adds version N+1."""
    last = db.scalar(select(DocumentTemplate).where(DocumentTemplate.kind == data.kind).order_by(DocumentTemplate.version.desc()).limit(1))
    for t in db.scalars(select(DocumentTemplate).where(DocumentTemplate.kind == data.kind, DocumentTemplate.is_active.is_(True))):
        t.is_active = False
    t = DocumentTemplate(kind=data.kind, version=(last.version + 1) if last else 1, body_ar=data.body_ar, body_en=data.body_en, is_active=True, created_by_id=actor.id)
    db.add(t)
    db.flush()
    audit.record(db, actor, "create", "document_template", t.id, {"kind": t.kind, "version": t.version})
    db.commit()
    db.refresh(t)
    return svc.template_out(t)


@router.get("/subscription-overview")
def subscription_overview(actor: User = Depends(staff), db: Session = Depends(get_db), days: int = Query(default=7, ge=1, le=60)):
    """Subscriptions ending within N days for the coach's (or all, for admin) clients."""
    ids = list(db.scalars(permissions.accessible_client_ids(actor)))
    out = []
    for cid in ids:
        sub = svc.latest_subscription(db, cid)
        left = svc.days_left(sub)
        if sub is not None and left is not None and 0 <= left <= days and sub.start_date <= date.today():
            client = db.get(User, cid)
            out.append({"client_id": cid, "client_name": client.full_name, **svc.subscription_out(sub)})
    out.sort(key=lambda x: x["days_left"])
    return out
