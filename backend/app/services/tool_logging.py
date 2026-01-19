import json
from datetime import datetime
from typing import Any

from ..config import LOG_DIR

AGENT_LOG_PATH = LOG_DIR / "agents.log"


def write_agent_log(entry: dict[str, Any], mode: str = "a") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry.setdefault("timestamp", datetime.utcnow().isoformat())
    with AGENT_LOG_PATH.open(mode, encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
