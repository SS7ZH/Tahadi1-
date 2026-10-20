"""Seed demo data.

    python -m app.db.seed               # admin + 2 trainers + 6 clients + ~3 months of history
    python -m app.db.seed --admin-only  # just the admin account (recommended for a real production launch)
    python -m app.db.seed --if-empty    # exit quietly (code 0) instead of failing when data already exists

Safety:
- Refuses to run when any user already exists (so it can never run twice against Supabase).
- The admin password comes from SEED_ADMIN_PASSWORD (required).
- Demo accounts use SEED_DEMO_PASSWORD (required in production; defaults to Demo@12345 elsewhere).
- Reference data (measurement definitions, activity factors) comes from the Alembic migration, not from here.
"""
import argparse
import random
import sys
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import (
    ClientProfile,
    Comment,
    MeasurementDefinition,
    MeasurementSession,
    MeasurementValue,
    Question,
    QuestionReply,
    User,
)

DEV_DEMO_PASSWORD = "Demo@12345"

TRAINERS = [
    {"full_name": "خالد العتيبي", "email": "trainer1@tahadi.app", "phone": "0500000001"},
    {"full_name": "نورة القحطاني", "email": "trainer2@tahadi.app", "phone": "0500000002"},
]

# (trainer index, profile, starting values, per-2-weeks drift)
CLIENTS = [
    (0, {"full_name": "عبدالله الشمري", "email": "client1@tahadi.app", "sex": "male", "birth_date": date(1994, 3, 12),
         "height_cm": 178, "goal": "fat_loss", "activity_key": "moderate"},
     {"weight": 96.0, "waist": 104, "hip": 108, "body_fat": 29.0, "pulse": 82, "sys": 134, "dia": 86}, -1.1),
    (0, {"full_name": "فهد الدوسري", "email": "client2@tahadi.app", "sex": "male", "birth_date": date(2000, 7, 2),
         "height_cm": 174, "goal": "muscle_gain", "activity_key": "high"},
     {"weight": 66.0, "waist": 78, "hip": 92, "body_fat": 14.0, "pulse": 68, "sys": 118, "dia": 76}, 0.6),
    (0, {"full_name": "سارة الحربي", "email": "client3@tahadi.app", "sex": "female", "birth_date": date(1990, 11, 20),
         "height_cm": 163, "goal": "health", "activity_key": "light"},
     {"weight": 74.0, "waist": 86, "hip": 104, "body_fat": 34.0, "pulse": 78, "sys": 126, "dia": 82}, -0.5),
    (1, {"full_name": "ريم الزهراني", "email": "client4@tahadi.app", "sex": "female", "birth_date": date(1997, 5, 8),
         "height_cm": 168, "goal": "fat_loss", "activity_key": "moderate"},
     {"weight": 82.0, "waist": 92, "hip": 112, "body_fat": 36.0, "pulse": 84, "sys": 128, "dia": 84}, -0.9),
    (1, {"full_name": "محمد الغامدي", "email": "client5@tahadi.app", "sex": "male", "birth_date": date(1985, 1, 30),
         "height_cm": 182, "goal": "fitness", "activity_key": "moderate"},
     {"weight": 85.0, "waist": 94, "hip": 102, "body_fat": 22.0, "pulse": 74, "sys": 130, "dia": 84}, -0.3),
    (1, {"full_name": "لمى السبيعي", "email": "client6@tahadi.app", "sex": "female", "birth_date": date(2002, 9, 15),
         "height_cm": 160, "goal": "muscle_gain", "activity_key": "high"},
     {"weight": 52.0, "waist": 66, "hip": 90, "body_fat": 22.0, "pulse": 70, "sys": 112, "dia": 72}, 0.4),
]

COMMENTS = [
    "بداية ممتازة! ركّز على شرب الماء والنوم الكافي هذا الأسبوع.",
    "تحسن واضح في القياسات، استمر على نفس البرنامج الغذائي.",
    "لاحظت تحسن في قوة القبضة والتحمل، أحسنت.",
    "نحتاج نرفع شدة تمارين الكارديو تدريجياً خلال الأسبوعين القادمين.",
]

QUESTIONS = [
    ("هل أقدر أتمرن يوم الجمعة بدل الخميس؟", "أكيد، المهم يكون فيه يوم راحة بين تمارين نفس العضلة."),
    ("وش أفضل وجبة قبل التمرين؟", None),
]


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed Tahadi demo data")
    p.add_argument("--admin-only", action="store_true", help="create only the admin account")
    p.add_argument("--if-empty", action="store_true", help="exit 0 instead of 1 when data already exists")
    return p.parse_args()


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _session_values(defs: dict[str, MeasurementDefinition], start: dict, drift: float, i: int,
                    height: float, rng: random.Random) -> list[MeasurementValue]:
    progress = i / 6  # 0 → 1 across the 3 months
    weight = round(start["weight"] + drift * i + rng.uniform(-0.3, 0.3), 1)
    waist_drift = drift * 0.9 if drift < 0 else drift * 0.2
    vals = {
        "weight": weight,
        "waist": round(start["waist"] + waist_drift * i + rng.uniform(-0.4, 0.4), 1),
        "hip": round(start["hip"] + (drift * 0.5 if drift < 0 else drift * 0.3) * i, 1),
        "body_fat": round(_clamp(start["body_fat"] + (-0.6 if drift < 0 else -0.2) * i + rng.uniform(-0.3, 0.3), 5, 60), 1),
        "chest": round(95 + drift * 0.5 * i + rng.uniform(-0.5, 0.5), 1),
        "arm": round(31 + (0.25 if drift > 0 else -0.1) * i, 1),
        "thigh": round(56 + (0.2 if drift > 0 else -0.35) * i, 1),
        "skinfold_triceps": round(_clamp(18 - 0.6 * i + rng.uniform(-0.5, 0.5), 3, 60), 1),
        "skinfold_subscapular": round(_clamp(20 - 0.7 * i + rng.uniform(-0.5, 0.5), 3, 60), 1),
        "skinfold_suprailiac": round(_clamp(22 - 0.8 * i + rng.uniform(-0.5, 0.5), 3, 60), 1),
        "pulse": round(start["pulse"] - 1.2 * i + rng.uniform(-2, 2)),
        "blood_sugar": round(95 + rng.uniform(-8, 8)),
        "hemoglobin": round(13.8 + rng.uniform(-0.6, 0.6), 1),
        "urine_color": int(_clamp(round(4 - progress * 2 + rng.uniform(-0.5, 0.5)), 1, 8)),
        "grip_strength": round(32 + 1.1 * i + rng.uniform(-0.8, 0.8), 1),
        "cardio_endurance": round(34 + 1.2 * i + rng.uniform(-0.6, 0.6), 1),
        "push_ups": int(14 + 2.5 * i + rng.randint(-1, 1)),
        "sit_ups": int(20 + 2 * i + rng.randint(-1, 1)),
        "agility": round(_clamp(14.5 - 0.35 * i + rng.uniform(-0.2, 0.2), 8, 30), 2),
        "flexibility": round(18 + 0.9 * i + rng.uniform(-0.5, 0.5), 1),
        "squat_assessment": int(_clamp(2 + round(progress * 3), 1, 5)),
        "body_shape": 4 if start["body_fat"] > 30 and progress < 0.5 else 3,
    }
    out = [MeasurementValue(definition=defs[k], value_number=float(v)) for k, v in vals.items() if k in defs]
    if i == 0 and "height" in defs:
        out.append(MeasurementValue(definition=defs["height"], value_number=float(height)))
    if "blood_pressure" in defs:
        sys_ = round(start["sys"] - 1.0 * i + rng.uniform(-2, 2))
        dia = round(start["dia"] - 0.6 * i + rng.uniform(-1.5, 1.5))
        out.append(MeasurementValue(definition=defs["blood_pressure"], value_number=float(sys_),
                                    value_json={"systolic": sys_, "diastolic": dia}))
    if "posture_analysis" in defs and i in (0, 6):
        text = "ميلان بسيط للكتفين للأمام وزيادة في تقعر أسفل الظهر." if i == 0 else "تحسن ملحوظ في استقامة الكتفين."
        out.append(MeasurementValue(definition=defs["posture_analysis"], value_text=text))
    return out


def main() -> int:
    args = _parse()
    admin_password = settings.SEED_ADMIN_PASSWORD
    if not admin_password or len(admin_password) < 8:
        print("ERROR: set SEED_ADMIN_PASSWORD (min 8 chars) before seeding.", file=sys.stderr)
        return 1
    demo_password = settings.SEED_DEMO_PASSWORD
    if not args.admin_only and not demo_password:
        if settings.is_production:
            print("ERROR: set SEED_DEMO_PASSWORD (or use --admin-only) in production.", file=sys.stderr)
            return 1
        demo_password = DEV_DEMO_PASSWORD

    db = get_sessionmaker()()
    try:
        try:
            existing_users = db.scalar(select(func.count()).select_from(User)) or 0
        except ProgrammingError:
            print("ERROR: tables do not exist yet. Run `alembic upgrade head` first.", file=sys.stderr)
            return 1
        if existing_users > 0:
            msg = "Database already contains users; seed refused (it only runs once)."
            if args.if_empty:
                print(msg + " Skipping.")
                return 0
            print("ERROR: " + msg, file=sys.stderr)
            return 1

        defs = {d.key: d for d in db.scalars(select(MeasurementDefinition))}
        if not defs:
            print("ERROR: no measurement definitions. Run `alembic upgrade head` first.", file=sys.stderr)
            return 1

        admin = User(full_name="مدير النظام", email=settings.SEED_ADMIN_EMAIL.lower(), role="admin",
                     password_hash=hash_password(admin_password))
        db.add(admin)
        if args.admin_only:
            db.commit()
            print(f"Created admin {admin.email}")
            return 0

        demo_hash = hash_password(demo_password)
        trainers = [User(**t, role="trainer", password_hash=demo_hash) for t in TRAINERS]
        db.add_all(trainers)
        db.flush()

        rng = random.Random(42)
        today = date.today()
        first_day = today - timedelta(days=84)
        for idx, (t_idx, prof, start, drift) in enumerate(CLIENTS):
            trainer = trainers[t_idx]
            client = User(full_name=prof["full_name"], email=prof["email"], phone=f"05510000{idx + 1:02d}",
                          role="client", password_hash=demo_hash)
            client.profile = ClientProfile(
                trainer_id=trainer.id, sex=prof["sex"], birth_date=prof["birth_date"], height_cm=prof["height_cm"],
                goal=prof["goal"], activity_key=prof["activity_key"],
            )
            db.add(client)
            db.flush()

            sessions = []
            for i in range(7):  # every 2 weeks ≈ 3 months
                s = MeasurementSession(
                    client_id=client.id, trainer_id=trainer.id, updated_by_id=trainer.id,
                    session_date=first_day + timedelta(days=14 * i),
                    notes="القياس الأولي" if i == 0 else None,
                )
                s.values = _session_values(defs, start, drift, i, prof["height_cm"], rng)
                db.add(s)
                sessions.append(s)
            db.flush()

            for j, body in enumerate(COMMENTS[: 2 + idx % 3]):
                db.add(Comment(client_id=client.id, session_id=sessions[min(j * 2, 6)].id,
                               author_id=trainer.id, body=body))
            db.add(Comment(client_id=client.id, author_id=trainer.id,
                           body="ملاحظة عامة: الالتزام ممتاز خلال الشهر الماضي، استمر."))

            q_text, answer = QUESTIONS[idx % 2]
            q = Question(client_id=client.id, session_id=sessions[-1].id, body=q_text,
                         status="answered" if answer else "open")
            if answer:
                q.replies.append(QuestionReply(author_id=trainer.id, body=answer))
            db.add(q)

        db.commit()
        print("Seed complete: 1 admin, 2 trainers, 6 clients, 42 sessions.")
        print(f"  admin:    {admin.email}  (password from SEED_ADMIN_PASSWORD)")
        print("  trainers: trainer1@tahadi.app, trainer2@tahadi.app")
        print("  clients:  client1..client6@tahadi.app")
        if demo_password == DEV_DEMO_PASSWORD:
            print(f"  demo password: {DEV_DEMO_PASSWORD}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
