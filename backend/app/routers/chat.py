import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import get_agent_credentials, get_agent_model
from ..db import SessionLocal, get_db
from ..deps import get_optional_user
from ..models import Conversation, Message, User
from ..schemas import ChatMessage, ChatRequest
from ..services.ai import call_ai_model_stream
from ..services.memory import fetch_latest_memory_summary, generate_memory_summary

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

AGENT_CONFIG = {
    "ideological": {
        "title": "Ideological Agent",
        "greeting": "I can help with ideological topics.",
    },
    "evaluation": {
        "title": "Evaluation Agent",
        "greeting": "I can help with evaluations.",
    },
    "task": {
        "title": "Task Agent",
        "greeting": "I can help with task guidance.",
    },
    "exploration": {
        "title": "Exploration Agent",
        "greeting": "I can help with exploration and research.",
    },
    "competition": {
        "title": "Competition Agent",
        "greeting": "I can help with competition preparation.",
    },
    "course": {
        "title": "Course Agent",
        "greeting": "I can help with course learning.",
    },
}


def _validate_messages(messages: list[ChatMessage] | None, field_name: str) -> list[dict]:
    if messages is None:
        return []
    cleaned: list[dict] = []
    for idx, msg in enumerate(messages):
        if not msg.role or not msg.content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} item {idx + 1} missing role or content",
            )
        if not msg.content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} item {idx + 1} has empty content",
            )
        cleaned.append({"role": msg.role.strip(), "content": msg.content.strip()})
    return cleaned


def _build_selected_hint(messages: list[dict], selected_messages: list[dict]) -> list[dict]:
    if not selected_messages:
        return messages

    lines = []
    for msg in selected_messages:
        role_label = "User" if msg.get("role") == "user" else "AI"
        lines.append(f"{role_label}: {msg.get('content', '')}")

    if not lines:
        return messages

    hint = "Selected conversation context:\n" + "\n".join(lines)

    if len(messages) <= 1:
        return messages + [{"role": "system", "content": hint}]

    merged = list(messages[:-1])
    merged.append({"role": "system", "content": hint})
    merged.append(messages[-1])
    return merged


def _attach_memory_prompt(messages: list[dict], memory_summary: str | None, agent_title: str) -> list[dict]:
    system_parts = [f"You are {agent_title}."]
    if memory_summary:
        system_parts.append("User memory summary:\n" + memory_summary)
    if system_parts:
        return [{"role": "system", "content": "\n\n".join(system_parts)}] + messages
    return messages


def _get_conversation(db: Session, conversation_id: int, user_id: int, agent: str) -> Conversation:
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.agent == agent,
        )
        .first()
    )
    if not convo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return convo


def _add_message(db: Session, conversation_id: int, role: str, content: str) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.utcnow(),
    )
    db.add(message)
    db.query(Conversation).filter(Conversation.id == conversation_id).update(
        {Conversation.updated_at: datetime.utcnow()}
    )
    db.commit()
    db.refresh(message)
    return message


@router.post("/api/agents/{agent}/chat")
def chat(
    payload: ChatRequest,
    agent: str = Path(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    agent_config = AGENT_CONFIG.get(agent)
    if not agent_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")

    api_key, base_url = get_agent_credentials(agent)
    model_name = get_agent_model(agent)
    if not api_key or not base_url or not model_name:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model not configured")

    messages = _validate_messages(payload.messages, "messages")
    selected_messages = _validate_messages(payload.selected_messages, "selected_messages")
    if not messages and payload.message:
        messages = [{"role": "user", "content": payload.message.strip()}]

    if not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one message required")

    if messages[-1]["role"] != "user":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Last message must be from user")

    is_guest = current_user is None
    if not is_guest and payload.conversation_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conversation_id is required")

    if not is_guest:
        convo = _get_conversation(db, payload.conversation_id, current_user.id, agent)
        _add_message(db, convo.id, "user", messages[-1]["content"])
        memory_summary = fetch_latest_memory_summary(db, current_user.id, agent)
    else:
        convo = None
        memory_summary = None
    messages_with_hint = _build_selected_hint(messages, selected_messages)
    messages_to_model = _attach_memory_prompt(
        messages_with_hint, memory_summary, agent_config.get("title", agent)
    )

    def event_generator():
        assistant_chunks: list[str] = []
        if is_guest:
            try:
                for chunk in call_ai_model_stream(
                    model_name, messages_to_model, api_key=api_key, base_url=base_url
                ):
                    if not chunk:
                        continue
                    assistant_chunks.append(chunk)
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            except Exception:
                logger.exception("Guest chat stream failed")
                yield f"data: {json.dumps({'error': 'service unavailable'})}\n\n"
            return

        assistant_message_id = None
        stream_completed = False
        with SessionLocal() as stream_db:
            try:
                for chunk in call_ai_model_stream(
                    model_name, messages_to_model, api_key=api_key, base_url=base_url
                ):
                    if not chunk:
                        continue
                    assistant_chunks.append(chunk)
                    full_text = "".join(assistant_chunks)
                    if assistant_message_id is None:
                        message = _add_message(stream_db, convo.id, "assistant", full_text)
                        assistant_message_id = message.id
                    else:
                        stream_db.query(Message).filter(Message.id == assistant_message_id).update(
                            {Message.content: full_text}
                        )
                        stream_db.query(Conversation).filter(Conversation.id == convo.id).update(
                            {Conversation.updated_at: datetime.utcnow()}
                        )
                        stream_db.commit()
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                stream_completed = True
            except Exception:
                logger.exception("Chat stream failed")
                yield f"data: {json.dumps({'error': 'service unavailable'})}\n\n"

            # Trigger memory summarization after successful completion
            if stream_completed:
                try:
                    generate_memory_summary(stream_db, current_user.id, agent)
                except Exception:
                    logger.exception("Memory summarization failed (non-blocking)")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
