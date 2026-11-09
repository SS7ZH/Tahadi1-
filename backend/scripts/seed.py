"""Seed synthetic demo data. Safe to re-run: deletes the seeded clients first.

Usage (from backend/):  python -m scripts.seed
"""

from datetime import date, timedelta

from app.db import get_db

# (name, weekly weights oldest -> newest, waists, days since last entry)
CLIENTS = [
    ("خالد العتيبي", [78.0, 77.2, 76.5, 75.6], [88.0, 87.0, 86.0, 85.0], 1),   # losing
    ("Omar Haddad", [92.4, 92.3, 92.5, 92.3], [101.0, 101.0, 100.5, 101.0], 2),  # stalled
    ("فهد القحطاني", [64.0, 64.6, 65.1, 65.8], [72.0, 72.5, 73.0, 73.5], 12),  # gaining, no check-in
]


def main() -> None:
    db = get_db()
    names = [c[0] for c in CLIENTS]
    db.table("clients").delete().in_("name", names).execute()  # cascades to child rows

    today = date.today()
    for name, weights, waists, days_ago in CLIENTS:
        client = db.table("clients").insert({"name": name}).execute().data[0]
        last = today - timedelta(days=days_ago)
        rows = [
            {
                "client_id": client["id"],
                "date": (last - timedelta(weeks=3 - i)).isoformat(),
                "weight_kg": w,
                "waist_cm": waists[i],
                "source": "app",
            }
            for i, w in enumerate(weights)
        ]
        db.table("measurements").insert(rows).execute()
        print(f"seeded {name}: {client['id']}")

    omar = db.table("clients").select("id").eq("name", "Omar Haddad").execute().data[0]
    db.table("form_checks").insert(
        {
            "client_id": omar["id"],
            "exercise": "squat",
            "reps": 8,
            "errors": [{"rep": 3, "type": "knees_caving"}, {"rep": 6, "type": "shallow_depth"}],
            "confidence": 0.82,
        }
    ).execute()
    print("seeded 1 form check")


if __name__ == "__main__":
    main()
