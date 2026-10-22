"""PDF exports. Every PDF: header (logo, title, coach, client, date), page X of Y, Arabic or English."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_accessible_client, get_current_user
from app.core.errors import not_found, unprocessable
from app.core.i18n import get_language, pick, tr
from app.db.session import get_db
from app.models import ActivityFactor, Comment, HealthDeclaration, MeasurementDefinition, SignedDocument, User
from app.pdf import charts
from app.pdf.render import content_disposition, filename, html_to_pdf, render_html
from app.schemas.nutrition import NutritionCalcIn
from app.services import audit, nutrition_plans, permissions, progress
from app.services import calculations as calc
from app.services import nutrition as nut
from app.services import onboarding as onb
from app.services import programs as prog
from app.services.serializers import value_display

router = APIRouter(prefix="/pdf", tags=["pdf"])
CHUNK = 6  # session columns per table


def _pdf(html: str, document: str, client_name: str | None) -> Response:
    return Response(
        content=html_to_pdf(html),
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition(filename(document, client_name)), "Cache-Control": "no-store"},
    )


def _coach_name(client: User | None) -> str | None:
    p = client.profile if client else None
    return p.trainer.full_name if p and p.trainer else None


# ---------------- program ----------------
@router.get("/program/{program_id}")
def program_pdf(program_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    program, client = prog.get_accessible_program(db, user, program_id)
    data = prog.program_out(program, client, include_today=False)
    for d in data["days"]:
        for it in d["items"]:
            it["display_name"] = pick(it["exercise_name_ar"], it["exercise_name_en"]) or it["custom_name"] or "—"
    coach = _coach_name(client) or (program.created_by.full_name if program.created_by else None)
    html = render_html("program.html", title_key="program", coach_name=coach, client_name=client.full_name if client else program.title, program=data)
    return _pdf(html, "program", client.full_name if client else "template")


# ---------------- contract / disclaimer ----------------
@router.get("/documents/{document_id}")
def signed_pdf(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(SignedDocument, document_id)
    client = db.get(User, doc.client_id) if doc else None
    if doc is None or client is None or not permissions.can_access_client(user, client):
        raise not_found(tr("المستند غير موجود", "Document not found"))
    declaration = None
    if doc.kind == "disclaimer" and doc.health_declaration_id:
        d = db.get(HealthDeclaration, doc.health_declaration_id)
        declaration = onb.declaration_out(d) if d else None
        audit.record(db, user, "export", "disclaimer_pdf", doc.id, {"client_id": client.id, "client_name": client.full_name})
        db.commit()
    html = render_html(
        "signed.html",
        title_key=doc.kind,
        coach_name=(doc.details or {}).get("coach_name") or _coach_name(client),
        client_name=client.full_name,
        doc=onb.signed_out(doc),
        declaration=declaration,
        signed_at=doc.signed_at.strftime("%Y-%m-%d %H:%M UTC"),
    )
    return _pdf(html, doc.kind, client.full_name)


# ---------------- measurements ----------------
@router.get("/measurements/{client_id}")
def measurements_pdf(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    keys: str | None = Query(default="weight,waist,body_fat", max_length=500),
    comments: bool = True,
    client: User = Depends(get_accessible_client),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lang = get_language()
    sessions = progress.load_sessions(db, client.id, date_from, date_to)
    defs = {d.key: d for d in db.scalars(select(MeasurementDefinition).order_by(MeasurementDefinition.sort_order))}

    # tables per category, at most CHUNK session columns each
    chunks = []
    for start in range(0, len(sessions), CHUNK):
        part = sessions[start : start + CHUNK]
        maps = [progress.value_map(s) for s in part]
        dates = [s.session_date.isoformat() for s in part]
        for cat in ("vital", "body", "movement", "physical"):
            rows = []
            for d in defs.values():
                if d.category != cat or not any(d.key in m for m in maps):
                    continue
                cells = [value_display(m[d.key]) if d.key in m else "" for m in maps]
                rows.append({"name": pick(d.name_ar, d.name_en), "unit": pick(d.unit, d.unit_en) if d.value_type == "number" else None, "cells": cells})
            if rows:
                chunks.append((cat, rows, dates))

    key_list = [k.strip() for k in (keys or "").split(",") if k.strip()][:8]
    series = progress.build_progress(db, client, key_list, date_from, date_to)["series"] if key_list else {}
    chart_list = [
        {
            "name": pick(s["name_ar"], s.get("name_en")),
            "unit": pick(s["unit"], s.get("unit_en")),
            "first": s["first"],
            "latest": s["latest"],
            "svg": charts.line_chart([(p["date"], p["value"]) for p in s["points"]], rtl=lang == "ar"),
        }
        for s in series.values()
        if s["points"]
    ]
    comment_rows = []
    if comments:
        stmt = select(Comment).where(Comment.client_id == client.id).order_by(Comment.created_at)
        for c in db.scalars(stmt).unique():
            d = c.created_at.date()
            if (date_from is None or d >= date_from) and (date_to is None or d <= date_to):
                comment_rows.append({"body": c.body, "author": c.author.full_name if c.author else "—", "date": d.isoformat()})

    summary = progress.build_summary(db, client)
    plan = nutrition_plans.current_plan(db, client.id)
    p = client.profile
    html = render_html(
        "measurements.html",
        title_key="measurements",
        coach_name=_coach_name(client),
        client_name=client.full_name,
        profile=p,
        age=calc.age_on(p.birth_date, date.today()) if p and p.birth_date else None,
        date_from=(date_from or (sessions[0].session_date if sessions else None)),
        date_to=(date_to or (sessions[-1].session_date if sessions else None)),
        results=summary["results"],
        plan=nutrition_plans.plan_out(plan) if plan else None,
        chunks=chunks,
        charts=chart_list,
        comments=comment_rows,
    )
    audit.record(db, user, "export", "measurements_pdf", client.id, {"client_id": client.id, "client_name": client.full_name})
    db.commit()
    return _pdf(html, "measurements", client.full_name)


# ---------------- calculator ----------------
class CalculatorPdfIn(NutritionCalcIn):
    model_config = ConfigDict(extra="forbid")

    client_id: int | None = None  # coach: pick one of their clients…
    client_name: str | None = Field(default=None, max_length=150)  # …or type a name (admin types both)
    coach_name: str | None = Field(default=None, max_length=150)


@router.post("/calculator")
def calculator_pdf(data: CalculatorPdfIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Names: coach → own name + chosen/typed client; player → own + their coach; admin → both typed.
    if user.role == "trainer":
        coach_name = user.full_name
        client_name = permissions.get_accessible_client(db, user, data.client_id).full_name if data.client_id else data.client_name
    elif user.role == "client":
        client_name, coach_name = user.full_name, _coach_name(user)
    else:
        coach_name, client_name = data.coach_name, data.client_name
    if not (coach_name or "").strip() or not (client_name or "").strip():
        raise unprocessable(tr("أدخل اسم المدرب واسم العميل للتصدير", "Enter both the coach and client names to export"), "NAMES_REQUIRED")

    factor = db.scalar(select(ActivityFactor).where(ActivityFactor.key == data.activity_key))
    if factor is None:
        raise unprocessable(tr("مستوى النشاط غير معروف", "Unknown activity level"), "UNKNOWN_ACTIVITY")
    settings = nutrition_plans.load_settings(db)[data.goal]
    bmr = calc.bmr_mifflin_st_jeor(data.sex, data.weight, data.height, data.age)
    tdee = calc.tdee(bmr, factor.factor)
    meals = data.meals_per_day if data.meals_per_day and settings.meals_min <= data.meals_per_day <= settings.meals_max else None
    html = render_html(
        "calculator.html",
        title_key="calculator",
        coach_name=coach_name.strip(),
        client_name=client_name.strip(),
        inputs=data,
        goal=data.goal,
        activity_name=pick(factor.name_ar, factor.name_en),
        activity_factor=factor.factor,
        bmr=bmr,
        tdee=tdee,
        plan=nut.build_plan(tdee, settings, meals_per_day=meals),
    )
    return _pdf(html, "calculator", client_name.strip())
