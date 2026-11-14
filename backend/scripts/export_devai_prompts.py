"""Copy the agents' instructions from DevAI Desktop into the repo.

The agents are built and edited in DevAI Desktop. When the backend runs them on Claude
(LLM_PROVIDER=claude, e.g. on Render), it sends these same instructions as the system
prompt. Re-run this after changing an agent in DevAI, then commit the files.

Usage (from backend/):  python -m scripts.export_devai_prompts
"""

import sys
from pathlib import Path

from app import config

DEVAI_AGENTS = Path.home() / ".devai" / "agents"
OUT = Path(__file__).resolve().parent.parent / "app" / "agents" / "prompts"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = False
    for key, agent_id in config.AGENT_IDS.items():
        src = DEVAI_AGENTS / (agent_id or f"<{key} agent id not set>") / "instructions" / "system-prompt.md"
        if not agent_id or not src.is_file():
            print(f"{key}: not found ({src})")
            missing = True
            continue
        dst = OUT / f"{key}.md"
        text = src.read_text(encoding="utf-8").strip() + "\n"
        changed = not dst.exists() or dst.read_text(encoding="utf-8") != text
        dst.write_text(text, encoding="utf-8")
        print(f"{key}: {agent_id} -> {dst.relative_to(OUT.parent.parent.parent)} ({'updated' if changed else 'unchanged'})")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
