"""Run each configured DevAI agent through the backend and check its reply format.

Usage (from backend/, with DevAI Desktop open):  python -m scripts.check_agents
"""

import json
import sys
import time

from app import config, llm
from app.rules.parsing import validate_measurement

CASES = {
    "intake": [
        ("صباح الخير، وزني اثنين وثمانين ونص", {"weight_kg": 82.5, "waist_cm": None}),
        ("خصري ٩٥", {"weight_kg": None, "waist_cm": 95.0}),
        ("90 today", None),
        ("متى التمرين القادم؟", None),
    ],
    "analyst": [
        (
            json.dumps(
                {
                    "client": "Omar Haddad",
                    "facts": {"entries": 4, "latest_date": "2026-11-07", "latest_weight_kg": 92.3,
                              "latest_waist_cm": 101.0, "weight_change_2w_kg": 0.0,
                              "weight_change_4w_kg": None, "waist_change_4w_cm": None, "days_since_last": 2},
                    "alerts": ["stalled"],
                },
                ensure_ascii=False,
            ),
            "summary",
        ),
    ],
    "coach": [
        (
            json.dumps(
                {
                    "client": "Omar Haddad",
                    "facts": {"entries": 4, "latest_weight_kg": 92.3, "weight_change_2w_kg": 0.0},
                    "alerts": ["stalled"],
                    "latest_form_check": {"exercise": "squat", "reps": 8, "confidence": 0.82,
                                          "errors": [{"rep": 3, "type": "knees_caving"}]},
                },
                ensure_ascii=False,
            ),
            "draft",
        ),
    ],
}


def parse_json(raw: str):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def check(agent: str, message: str, expected) -> bool:
    start = time.time()
    try:
        raw = llm.run_agent(config.AGENT_IDS[agent], message, name=f"Tahadi check {agent}")
    except (llm.LLMError, llm.LLMNotConfigured) as exc:
        print(f"  FAIL  {message[:40]!r}: {exc}")
        return False
    secs = time.time() - start
    try:
        if expected == "draft":
            ok = bool(raw.strip()) and not raw.strip().startswith("{")
        elif expected == "summary":
            out = parse_json(raw)
            ok = set(out) == {"summary_ar", "summary_en"} and "92.3" in out["summary_en"]
        else:
            ok = validate_measurement(parse_json(raw)) == expected
    except (json.JSONDecodeError, AttributeError, TypeError):
        ok = False
    print(f"  {'PASS' if ok else 'FAIL'}  ({secs:.1f}s) {message[:40]!r} -> {raw.strip()[:160]!r}")
    return ok


def main() -> None:
    if not config.DEVAI_API_KEY:
        sys.exit("Set DEVAI_API_KEY in backend/.env first.")
    results = []
    for agent, cases in CASES.items():
        agent_id = config.AGENT_IDS[agent]
        if not agent_id:
            print(f"{agent}: skipped (no agent id in .env)")
            continue
        print(f"{agent} ({agent_id}, model {config.DEVAI_MODEL}):")
        results += [check(agent, msg, exp) for msg, exp in cases]
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if results and all(results) else 1)


if __name__ == "__main__":
    main()
