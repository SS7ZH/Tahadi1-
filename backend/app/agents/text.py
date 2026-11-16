"""Text produced by the three agents built in DevAI Desktop, with fixed templates as fallback.

The agents only receive facts computed in code (app.rules); the backend range-checks
anything they return. Input/output contracts: docs/devai-agents.md.
"""

import json
import logging

from app import llm

log = logging.getLogger("tahadi.agents")


def ask_agent(agent: str, payload: str) -> str | None:
    """Run one DevAI agent; None if it isn't configured or the call failed (caller uses a template)."""
    try:
        text = llm.ask(agent, payload).strip()
        return text or None
    except llm.LLMNotConfigured:
        return None
    except llm.LLMError as exc:
        log.warning("agent %s failed, using template: %s", agent, exc)
        return None


def _json(raw: str | None) -> dict | None:
    if not raw:
        return None
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


# ---------- intake agent ----------

def extract_measurement(text: str) -> dict | None:
    """Fallback when the regex found nothing. The caller range-checks the result."""
    return _json(ask_agent("intake", text))


def confirmation(values: dict, arabic: bool) -> str:
    parts = []
    if values.get("weight_kg") is not None:
        parts.append(f"الوزن {values['weight_kg']:g} كجم" if arabic else f"weight {values['weight_kg']:g} kg")
    if values.get("waist_cm") is not None:
        parts.append(f"الخصر {values['waist_cm']:g} سم" if arabic else f"waist {values['waist_cm']:g} cm")
    if arabic:
        return "تم تسجيل " + " و".join(parts) + " ✅ شكرًا لك!"
    return "Saved " + " and ".join(parts) + " ✅ Thank you!"


def not_a_measurement(arabic: bool) -> str:
    if arabic:
        return "شكرًا لرسالتك! سيرد عليك مدربك قريبًا."
    return "Thanks for your message! Your coach will reply soon."


NOT_LINKED = "Your account isn't linked yet. Ask your coach for a code."


# ---------- progress analyst agent ----------

def _template_summary(name: str, facts: dict, alerts: list[str]) -> tuple[str, str]:
    if not facts.get("entries"):
        return (f"لا توجد قياسات بعد لـ {name}.", f"No measurements yet for {name}.")
    ar, en = [], []
    w = facts.get("latest_weight_kg")
    if w is not None:
        ar.append(f"آخر وزن مسجل لـ {name} هو {w:g} كجم.")
        en.append(f"{name}'s latest weight is {w:g} kg.")
    c = facts.get("weight_change_4w_kg")
    if c is None:
        c, ar_period, en_period = facts.get("weight_change_2w_kg"), "أسبوعين", "2 weeks"
    else:
        ar_period, en_period = "4 أسابيع", "4 weeks"
    if c is not None:
        ar.append(f"التغير خلال {ar_period}: {c:+g} كجم.")
        en.append(f"Change over {en_period}: {c:+g} kg.")
    if "stalled" in alerts:
        ar.append("الوزن ثابت تقريبًا منذ 3 أسابيع.")
        en.append("Weight has barely moved for 3 weeks.")
    if "no_checkin" in alerts:
        ar.append(f"لم يسجل أي قياس منذ {facts['days_since_last']} يومًا.")
        en.append(f"No check-in for {facts['days_since_last']} days.")
    return " ".join(ar), " ".join(en)


def summary_result(name: str, facts: dict, alerts: list[str]) -> dict:
    """Progress Analyst agent; {"summary_ar", "summary_en", "source": "agent" | "template"}."""
    payload = json.dumps({"client": name, "facts": facts, "alerts": alerts}, ensure_ascii=False)
    out = _json(ask_agent("analyst", payload)) or {}
    ar, en = out.get("summary_ar"), out.get("summary_en")
    if isinstance(ar, str) and ar.strip() and isinstance(en, str) and en.strip():
        return {"summary_ar": ar.strip(), "summary_en": en.strip(), "source": "agent"}
    t_ar, t_en = _template_summary(name, facts, alerts)
    return {"summary_ar": t_ar, "summary_en": t_en, "source": "template"}


def summary(name: str, facts: dict, alerts: list[str]) -> tuple[str, str]:
    r = summary_result(name, facts, alerts)
    return r["summary_ar"], r["summary_en"]


# ---------- coach assistant agent ----------

FORM_TIPS_AR = {
    "knees_caving": "حافظ على ركبتيك باتجاه أصابع القدم",
    "shallow_depth": "انزل أكثر في السكوات",
    "back_lean": "حافظ على استقامة ظهرك",
}
LOW_CONFIDENCE = 0.6


def _template_draft(name: str, facts: dict, alerts: list[str], form_check: dict | None, question: str | None = None) -> str:
    first = name.split()[0]
    lines = [f"مرحبًا {first} 👋"]
    if question:
        # Without the agent we cannot answer the question itself: acknowledge it for the coach to complete.
        lines.append("شكرًا على سؤالك، سأراجعه وأرد عليك بالتفصيل قريبًا.")
        return "\n".join(lines)
    if not facts.get("entries"):
        lines.append("أرسل وزنك اليوم لنبدأ متابعة تقدمك.")
    elif "no_checkin" in alerts:
        lines.append("افتقدنا قياساتك، أرسل وزنك اليوم لنتابع تقدمك.")
    elif "stalled" in alerts:
        lines.append("وزنك ثابت منذ ثلاثة أسابيع، لا تقلق — سنعدل الخطة معًا هذا الأسبوع.")
    elif (facts.get("weight_change_2w_kg") or 0) < 0:
        lines.append("تقدم ممتاز! استمر على نفس الالتزام.")
    else:
        lines.append("شكرًا على التزامك بالتسجيل، لنراجع أهدافك هذا الأسبوع.")
    if form_check:
        confidence = form_check.get("confidence")
        if confidence is not None and float(confidence) < LOW_CONFIDENCE:
            lines.append("فيديو السكوات غير واضح، أعد تصويره من الجانب وفي إضاءة جيدة.")
        else:
            types = [e.get("type") for e in (form_check.get("errors") or []) if isinstance(e, dict)]
            tips = list(dict.fromkeys(FORM_TIPS_AR[t] for t in types if t in FORM_TIPS_AR))[:2]
            if tips:
                lines.append("ملاحظات على السكوات: " + "، ".join(tips) + ".")
    return "\n".join(lines)


def draft_result(
    name: str, facts: dict, alerts: list[str], form_check: dict | None, question: str | None = None
) -> tuple[str, str]:
    """Coach Assistant agent; (text, "agent" | "template"). With `question`, the draft answers it."""
    data = {"client": name, "facts": facts, "alerts": alerts, "latest_form_check": form_check}
    if question:
        data["question"] = question
    text = ask_agent("coach", json.dumps(data, ensure_ascii=False, default=str))
    if text:
        return text, "agent"
    return _template_draft(name, facts, alerts, form_check, question), "template"


def draft(name: str, facts: dict, alerts: list[str], form_check: dict | None, question: str | None = None) -> str:
    return draft_result(name, facts, alerts, form_check, question)[0]
