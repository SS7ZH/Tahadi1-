"""Player-side: the 3-step first-login wizard, file uploads, and later health-declaration updates."""
from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.core.errors import AppError, not_found, unprocessable
from app.core.i18n import tr
from app.db.session import get_db
from app.models import HealthDeclaration, MedicalFile, SubscriptionPlan, User
from app.schemas.onboarding import ContractSignIn, HealthOnboardingIn, HealthUpdateIn, SubscriptionStartIn
from app.services import audit, storage
from app.services import onboarding as svc

router = APIRouter(tags=["onboarding"])
player = require_role("client")


@router.get("/onboarding")
def get_status(user: User = Depends(player), db: Session = Depends(get_db)):
    plans = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.sort_order)).all()
    pending = db.scalars(
        select(MedicalFile).where(MedicalFile.client_id == user.id, MedicalFile.declaration_id.is_(None)).order_by(MedicalFile.id)
    ).all()
    return {
        **svc.status(db, user),
        "plans": [svc.plan_out(p) for p in plans],
        "pending_files": [svc.file_out(f) for f in pending],
        "coach_name": user.profile.trainer.full_name if user.profile and user.profile.trainer else None,
    }


@router.post("/onboarding/subscription", status_code=status.HTTP_201_CREATED)
def choose_subscription(data: SubscriptionStartIn, user: User = Depends(player), db: Session = Depends(get_db)):
    if svc.latest_subscription(db, user.id) is not None:
        # After the first choice only the coach/admin can change dates, extend or renew.
        raise AppError(409, "SUBSCRIPTION_EXISTS", tr("الاشتراك محدد مسبقاً؛ تواصل مع مدربك للتعديل", "Your subscription is already set; contact your coach to change it"))
    plan = svc.get_plan(db, data.plan_id)
    sub = svc.create_subscription(db, user, user, plan, data.start_date, "initial")
    db.commit()
    return svc.subscription_out(sub)


async def _read_upload(file: UploadFile) -> bytes:
    chunks, total = [], 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        storage.check_size(total)  # stop reading as soon as it is too big
        chunks.append(chunk)
    data = b"".join(chunks)
    storage.check_size(len(data))
    return data


@router.post("/onboarding/files", status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...), user: User = Depends(player), db: Session = Depends(get_db)):
    """Optional medical report (PDF/JPG/PNG ≤ 10 MB). Stays 'pending' until attached to a declaration."""
    pending = db.scalar(
        select(func.count()).select_from(MedicalFile).where(MedicalFile.client_id == user.id, MedicalFile.declaration_id.is_(None))
    )
    if pending >= storage.MAX_FILES:
        raise unprocessable(tr("الحد الأقصى 3 ملفات", "You can attach up to 3 files"), "TOO_MANY_FILES")
    data = await _read_upload(file)
    mime, ext = storage.sniff(data)
    path = storage.new_path(user.id, ext)
    storage.save(path, data, mime)
    row = MedicalFile(
        client_id=user.id,
        storage_path=path,
        original_name=(file.filename or f"file.{ext}")[-200:],
        content_type=mime,
        size_bytes=len(data),
        uploaded_by_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return svc.file_out(row)


@router.delete("/onboarding/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_pending_file(file_id: int, user: User = Depends(player), db: Session = Depends(get_db)):
    row = db.get(MedicalFile, file_id)
    if row is None or row.client_id != user.id or row.declaration_id is not None:
        raise not_found(tr("الملف غير موجود", "File not found"))
    db.delete(row)  # the stored object is left orphaned in the private bucket; harmless and not reachable
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/onboarding/disclaimer")
def get_disclaimer(user: User = Depends(player), db: Session = Depends(get_db)):
    return svc.rendered_template(db, user, "disclaimer")


@router.get("/onboarding/contract")
def get_contract(user: User = Depends(player), db: Session = Depends(get_db)):
    sub = svc.latest_subscription(db, user.id)
    if sub is None:
        raise AppError(409, "STEP_ORDER", tr("اختر مدة الاشتراك أولاً", "Choose your subscription first"))
    return {**svc.rendered_template(db, user, "contract"), "subscription": svc.subscription_out(sub)}


def _attach_files(db: Session, user: User, declaration: HealthDeclaration, file_ids: list[int]) -> None:
    for fid in file_ids:
        f = db.get(MedicalFile, fid)
        if f is None or f.client_id != user.id or f.declaration_id is not None:
            raise not_found(tr("الملف غير موجود", "File not found"))
        f.declaration_id = declaration.id


def _new_declaration(db: Session, user: User, data) -> HealthDeclaration:
    decl = HealthDeclaration(
        client_id=user.id,
        has_chronic=data.has_chronic,
        conditions=data.conditions,
        details=(data.details or "").strip() or None,
        medications=(data.medications or "").strip() or None,
        injuries=(data.injuries or "").strip() or None,
    )
    db.add(decl)
    db.flush()
    _attach_files(db, user, decl, data.file_ids)
    return decl


@router.post("/onboarding/health", status_code=status.HTTP_201_CREATED)
def submit_health(data: HealthOnboardingIn, request: Request, user: User = Depends(player), db: Session = Depends(get_db)):
    """Step 2: health declaration + disclaimer signature, saved together."""
    if svc.latest_subscription(db, user.id) is None:
        raise AppError(409, "STEP_ORDER", tr("اختر مدة الاشتراك أولاً", "Choose your subscription first"))
    if svc.has_signed(db, user.id, "disclaimer"):
        raise AppError(409, "ALREADY_SIGNED", tr("تم توقيع الإقرار مسبقاً", "The disclaimer is already signed"))
    typed = svc.check_signature(user, data.typed_name, data.agreed)
    decl = _new_declaration(db, user, data)
    svc.sign(db, user, kind="disclaimer", template_id=data.template_id, typed_name=typed, request=request, declaration=decl)
    db.commit()
    return svc.status(db, user)


@router.post("/onboarding/contract", status_code=status.HTTP_201_CREATED)
def sign_contract(data: ContractSignIn, request: Request, user: User = Depends(player), db: Session = Depends(get_db)):
    """Step 3: contract for the latest subscription (renewals bring the client back here)."""
    st = svc.status(db, user)
    if not st["steps"]["subscription"] or not st["steps"]["health"]:
        raise AppError(409, "STEP_ORDER", tr("أكمل الخطوات السابقة أولاً", "Complete the previous steps first"))
    sub = svc.latest_subscription(db, user.id)
    if svc.has_signed(db, user.id, "contract", sub.id):
        raise AppError(409, "ALREADY_SIGNED", tr("تم توقيع العقد مسبقاً", "The contract is already signed"))
    typed = svc.check_signature(user, data.typed_name, data.agreed)
    doc = svc.sign(db, user, kind="contract", template_id=data.template_id, typed_name=typed, request=request, subscription=sub)
    db.flush()
    audit.record(db, user, "create", "signed_document", doc.id, {"client_id": user.id, "client_name": user.full_name, "kind": "contract"})
    db.commit()
    return svc.status(db, user)


@router.post("/me/health-declaration", status_code=status.HTTP_201_CREATED)
def update_health(data: HealthUpdateIn, user: User = Depends(player), db: Session = Depends(get_db)):
    """Later update from the profile: a new version (previous kept); the coach sees an 'updated' badge."""
    decl = _new_declaration(db, user, data)
    audit.record(db, user, "create", "health_declaration", decl.id, {"client_id": user.id, "client_name": user.full_name})
    db.commit()
    db.refresh(decl)
    return svc.declaration_out(decl)


@router.post("/me/files", status_code=status.HTTP_201_CREATED)
async def upload_file_later(file: UploadFile = File(...), user: User = Depends(player), db: Session = Depends(get_db)):
    """Same as the onboarding upload, for declaration updates after onboarding."""
    return await upload_file(file=file, user=user, db=db)
