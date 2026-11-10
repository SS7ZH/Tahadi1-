import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "tahadi_coach_bot").removeprefix("@")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

# DevAI Desktop agents (see app/llm.py and docs/devai-agents.md)
DEVAI_HOST_URL = os.getenv("DEVAI_HOST_URL", "http://127.0.0.1:7588").rstrip("/")
DEVAI_API_KEY = os.getenv("DEVAI_API_KEY", "")
DEVAI_MODEL = os.getenv("DEVAI_MODEL", "DeepSeek-V4.1-Flash")
AGENT_IDS = {
    "intake": os.getenv("DEVAI_INTAKE_AGENT_ID", ""),
    "analyst": os.getenv("DEVAI_ANALYST_AGENT_ID", ""),
    "coach": os.getenv("DEVAI_COACH_AGENT_ID", ""),
}

ALLOWED_ORIGINS = [o for o in [FRONTEND_URL, "http://localhost:5173"] if o]
