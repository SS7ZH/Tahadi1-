"""Showcase accounts for demonstrating the site: one coach and one trainee with ~3 months of synthetic data.

    SHOWCASE_PASSWORD='...' python -m app.db.seed_showcase

- Works on a database that already has data (unlike app.db.seed); refuses if either email already exists.
- Both accounts get SHOWCASE_PASSWORD (required, min 8 chars). It is never printed.
- The trainee is fully onboarded (subscription, health declaration, signed disclaimer + contract)
  so the demo opens straight on the dashboard. All data is synthetic.
"""
import os
import random
import sys
from datetime import date, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.seed import _session_values
from app.db.session import get_sessionmaker
from app.models import (
    ClientProfile,
    Comment,
    Exercise,
    HealthDeclaration,
    MeasurementDefinition,
    MeasurementSession,
    Question,
    QuestionReply,
    SignedDocument,
    SubscriptionPlan,
    User,
)
from app.schemas.nutrition import NutritionPlanIn
from app.schemas.program import ProgramIn
from app.services import nutrition_plans
from app.services import onboarding as onb
from app.services import programs as prog

COACH = {"full_name": "عيشه الزهراني", "email": "aisha.coach@tahadi.app", "phone": "0559900001"}
TRAINEE = {"full_name": "هيا العمري", "email": "haya.trainee@tahadi.app", "phone": "0559900002"}
PROFILE = {"sex": "female", "birth_date": date(1996, 4, 18), "height_cm": 165, "goal": "fat_loss", "activity_key": "moderate"}
START = {"weight": 78.0, "waist": 89, "hip": 108, "body_fat": 33.0, "pulse": 80, "sys": 124, "dia": 80}
DRIFT = -0.8  # kg per 2 weeks

SESSION_NOTES = ["القياس الأولي", None, "التزام ممتاز بالتمارين", None, "تحسن في التحمل", None, "نهاية المرحلة الأولى"]
COMMENTS = [
    (0, "بداية موفقة يا هيا! ركّزي على شرب 2.5 لتر ماء يومياً والنوم 7 ساعات."),
    (2, "نزول واضح في محيط الخصر، استمري على نفس الخطة الغذائية."),
    (4, "قوة القبضة وتمارين الضغط تحسنت بشكل ممتاز، بنرفع الأوزان الأسبوع الجاي."),
    (6, "أحسنتِ! خسرتِ قرابة 5 كجم خلال 3 أشهر مع تحسن في اللياقة. نبدأ المرحلة الثانية."),
]
QUESTIONS = [
    (3, "هل أقدر أبدّل تمرين الجري بالدراجة الثابتة؟", "نعم، الدراجة بنفس المدة ونفس منطقة النبض تعطيك نفس الفائدة."),
    (6, "كم وجبة أفضل لي في اليوم؟", None),
]


def _program(exercise_ids: list[int | None], start: date) -> ProgramIn:
    ex = (exercise_ids + [None] * 6)[:6]

    def res(i, sets, reps, load, rest=90):
        item = {"kind": "resistance", "sets": sets, "reps": reps, "load_value": load, "load_unit": "kg", "rest_seconds": rest}
        return {**item, "exercise_id": ex[i]} if ex[i] else {**item, "custom_name": f"تمرين {i + 1}"}

    return ProgramIn.model_validate({
        "title": "برنامج خسارة الدهون – المرحلة الثانية",
        "goal": "خسارة الدهون مع المحافظة على الكتلة العضلية",
        "start_date": start.isoformat(),
        "weeks": 6,
        "days_per_week": 4,
        "notes": "حافظي على تقنية الأداء قبل زيادة الأوزان، وسجّلي الأوزان المستخدمة في كل تمرين.",
        "days": [
            {"day_number": 1, "title": "الجزء العلوي", "warmup": "5 دقائق دراجة + تمارين حركية للكتف",
             "items": [res(0, 4, "10-12", 20), res(1, 3, "12", 15), res(2, 3, "12-15", 8, 60),
                       {"kind": "cardio", "cardio_type": "treadmill", "duration_min": 20, "hr_zone": 2, "incline": 6}],
             "cooldown": "إطالات 5 دقائق"},
            {"day_number": 2, "title": "الجزء السفلي", "warmup": "5 دقائق مشي سريع",
             "items": [res(3, 4, "10", 30, 120), res(4, 3, "12", 25), res(5, 3, "15", 10, 60)],
             "cooldown": "إطالات للأرجل"},
            {"day_number": 3, "title": "راحة نشطة", "is_rest": True, "notes": "مشي خفيف 30 دقيقة"},
            {"day_number": 4, "title": "كارديو متقطع + بطن", "warmup": "5 دقائق جري خفيف",
             "items": [{"kind": "cardio", "cardio_type": "hiit", "duration_min": 15, "hr_zone": 4,
                        "work_seconds": 30, "interval_rest_seconds": 30, "rounds": 12},
                       {"kind": "resistance", "custom_name": "بلانك (45 ثانية)", "sets": 3, "reps": "1", "rest_seconds": 45}]},
        ],
    })


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    password = os.environ.get("SHOWCASE_PASSWORD") or ""
    if len(password) < 8:
        print("ERROR: set SHOWCASE_PASSWORD (min 8 chars).", file=sys.stderr)
        return 1

    db = get_sessionmaker()()
    try:
        emails = [COACH["email"], TRAINEE["email"]]
        taken = db.scalars(select(User.email).where(User.email.in_(emails))).all()
        if taken:
            print(f"Already exists: {', '.join(taken)}. Nothing changed.")
            return 0
        defs = {d.key: d for d in db.scalars(select(MeasurementDefinition))}
        plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).order_by(SubscriptionPlan.months.desc()))
        if not defs or plan is None:
            print("ERROR: run `alembic upgrade head` first (needs measurement definitions and an active plan).", file=sys.stderr)
            return 1

        today = date.today()
        first_day = today - timedelta(days=84)
        exercise_ids = list(db.scalars(select(Exercise.id).order_by(Exercise.id).limit(6)))
        program_in = _program(exercise_ids, today - timedelta(days=today.weekday() + 1))

        pw = hash_password(password)
        coach = User(**COACH, role="trainer", password_hash=pw)
        db.add(coach)
        db.flush()
        trainee = User(**TRAINEE, role="client", password_hash=pw)
        trainee.profile = ClientProfile(trainer_id=coach.id, **PROFILE)
        db.add(trainee)
        db.flush()
        db.refresh(trainee)

        # onboarding: subscription → health declaration + disclaimer → contract
        sub = onb.create_subscription(db, coach, trainee, plan, first_day, "initial")
        decl = HealthDeclaration(client_id=trainee.id, has_chronic=False, conditions=[], injuries="لا يوجد")
        db.add(decl)
        db.flush()
        for kind in ("disclaimer", "contract"):
            t = onb.active_template(db, kind)
            ctx = onb.template_context(trainee, sub, "ar")
            db.add(SignedDocument(
                client_id=trainee.id, kind=kind, template_id=t.id, template_version=t.version, language="ar",
                rendered_text=onb.render(t.body_ar, ctx), typed_name=trainee.full_name,
                ip_address="showcase", user_agent="showcase seed",
                subscription_id=sub.id if kind == "contract" else None,
                health_declaration_id=decl.id if kind == "disclaimer" else None,
                details={k: ctx[k] for k in ("client_name", "coach_name", "plan", "start_date", "end_date", "price")},
            ))

        # 7 sessions, every 2 weeks
        rng = random.Random(7)
        sessions = []
        for i in range(7):
            s = MeasurementSession(client_id=trainee.id, trainer_id=coach.id, updated_by_id=coach.id,
                                   session_date=first_day + timedelta(days=14 * i), notes=SESSION_NOTES[i])
            s.values = _session_values(defs, START, DRIFT, i, PROFILE["height_cm"], rng)
            db.add(s)
            sessions.append(s)
        db.flush()
        for i, body in COMMENTS:
            db.add(Comment(client_id=trainee.id, session_id=sessions[i].id, author_id=coach.id, body=body))
        for i, body, answer in QUESTIONS:
            q = Question(client_id=trainee.id, session_id=sessions[i].id, body=body, status="answered" if answer else "open")
            if answer:
                q.replies.append(QuestionReply(author_id=coach.id, body=answer))
            db.add(q)

        nutrition_plans.save_plan(db, coach, trainee, NutritionPlanIn(meals_per_day=4, note="ركّزي على البروتين في كل وجبة والخضار في الغداء والعشاء."))
        db.commit()

        program = prog.create_program(db, coach, program_in, client=trainee, is_template=False)
        prog.activate(db, coach, program, trainee)

        print("Showcase accounts created (password = SHOWCASE_PASSWORD):")
        print(f"  coach:   {COACH['email']}  ({COACH['full_name']})")
        print(f"  trainee: {TRAINEE['email']}  ({TRAINEE['full_name']}) — 7 sessions, nutrition plan, active program")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
