import re
from typing import Any

from sqlalchemy.orm import Session

from ..models import AgentRun, AgentRunTrace
from .tool_logging import write_agent_log

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b\d{11}\b")


def _sanitize_text(text: str | None) -> str | None:
    if not text:
        return text
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text


def write_agent_run(db: Session, payload: dict[str, Any]) -> int | None:
    record = AgentRun(
        agent=payload.get("agent"),
        user_id=payload.get("user_id"),
        conversation_id=payload.get("conversation_id"),
        profile_id=payload.get("profile_id"),
        profile_version=payload.get("profile_version"),
        request_text=_sanitize_text(payload.get("request_text")),
        plan_json=payload.get("plan_json"),
        tool_summary=payload.get("tool_summary"),
        final_answer=payload.get("final_answer"),
        latency_ms=payload.get("latency_ms"),
        cost=payload.get("cost"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    write_agent_log(
        {
            "event": "agent_run_saved",
            "agent": record.agent,
            "conversation_id": record.conversation_id,
            "user_id": record.user_id,
            "agent_run_id": record.id,
        }
    )
    return record.id


def write_agent_run_trace(db: Session, payload: dict[str, Any]) -> int | None:
    record = AgentRunTrace(
        agent_run_id=payload.get("agent_run_id"),
        agent=payload.get("agent"),
        user_id=payload.get("user_id"),
        conversation_id=payload.get("conversation_id"),
        user_message_id=payload.get("user_message_id"),
        request_text=_sanitize_text(payload.get("request_text")),
        trace=payload.get("trace") or [],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    write_agent_log(
        {
            "event": "agent_run_trace_saved",
            "agent": record.agent,
            "conversation_id": record.conversation_id,
            "user_id": record.user_id,
            "agent_run_trace_id": record.id,
        }
    )
    return record.id
