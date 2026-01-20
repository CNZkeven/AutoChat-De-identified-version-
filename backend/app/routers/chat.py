import json
import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import get_agent_credentials, get_agent_model
from ..db import SessionLocal, get_db
from ..deps import get_optional_user
from ..models import Conversation, Message, User
from ..schemas import ChatMessage, ChatRequest
from ..services.agent_profiles import (
    get_agent_allowed_tools_from_profile,
    get_agent_profile,
)
from ..services.agent_prompts import get_agent_allowed_tools, get_agent_system_prompt
from ..services.agent_router import resolve_agent
from ..services.agent_run_logger import write_agent_run, write_agent_run_trace
from ..services.memory import fetch_latest_memory_summary, generate_memory_summary
from ..services.orchestrator import (
    FINAL_TOOL_INSTRUCTION,
    _build_tool_messages,
    build_missing_slots_question,
    execute_plan,
    identify_missing_slots,
    plan_with_tools,
    stream_without_tools,
    synthesize_with_tools,
)
from ..services.title import generate_conversation_title
from ..services.tool_logging import write_agent_log
from ..services.tool_registry import load_tool_registry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

AGENT_CONFIG = {
    "ideological": {
        "title": "思政智能体",
        "greeting": "我可以帮助你讨论思想政治相关话题。",
    },
    "evaluation": {
        "title": "评价智能体",
        "greeting": "我可以帮助你进行学习评价与反馈。",
    },
    "task": {
        "title": "任务智能体",
        "greeting": "我可以帮助你进行任务规划与执行。",
    },
    "exploration": {
        "title": "探究智能体",
        "greeting": "我可以帮助你进行探究式学习与研究。",
    },
    "competition": {
        "title": "竞赛智能体",
        "greeting": "我可以帮助你准备各类学科竞赛。",
    },
    "course": {
        "title": "课程智能体",
        "greeting": "我可以帮助你学习课程内容。",
    },
}

PROMPT_TEMPLATE_PATH = "backend/app/services/agent_prompts.py"


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
        role_label = "用户" if msg.get("role") == "user" else "智能体"
        lines.append(f"{role_label}: {msg.get('content', '')}")

    if not lines:
        return messages

    hint = "选中对话内容：\n" + "\n".join(lines)

    if len(messages) <= 1:
        return messages + [{"role": "system", "content": hint}]

    merged = list(messages[:-1])
    merged.append({"role": "system", "content": hint})
    merged.append(messages[-1])
    return merged


def _attach_memory_prompt(
    messages: list[dict],
    memory_summary: str | None,
    agent_title: str,
    agent: str,
    user_id: int | None,
) -> list[dict]:
    system_prompt = get_agent_system_prompt(agent)
    if system_prompt:
        system_parts = [system_prompt]
    else:
        system_parts = [f"你是{agent_title}。"]
    if memory_summary:
        system_parts.append("用户记忆摘要：\n" + memory_summary)
    if user_id is not None:
        system_parts.append(f"当前用户ID：{user_id}（用于工具调用）")
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


def _add_message(
    db: Session, conversation_id: int, role: str, content: str, user_id: int | None
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        user_id=user_id,
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
    messages = _validate_messages(payload.messages, "messages")
    selected_messages = _validate_messages(payload.selected_messages, "selected_messages")
    if not messages and payload.message:
        messages = [{"role": "user", "content": payload.message.strip()}]

    if not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one message required")

    if messages[-1]["role"] != "user":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Last message must be from user")

    resolved_agent = agent
    routing_decision = None
    if agent in {"auto", "router"}:
        last_user_content = messages[-1]["content"] if messages else (payload.message or "")
        decision = resolve_agent(
            last_user_content,
            list(AGENT_CONFIG.keys()),
            default_agent="ideological",
        )
        routing_decision = decision
        resolved_agent = decision.get("agent_id", "ideological")
        write_agent_log(
            {
                "event": "routing_decision",
                "agent": resolved_agent,
                "conversation_id": None,
                "user_id": current_user.id if current_user else None,
                "decision": decision,
            }
        )
        if decision.get("missing_slots"):
            clarify_text = build_missing_slots_question(decision.get("missing_slots"))
            return StreamingResponse(
                iter([f"data: {json.dumps({'content': clarify_text})}\\n\\n"]),
                media_type="text/event-stream",
            )

    agent_config = AGENT_CONFIG.get(resolved_agent)
    if not agent_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")

    api_key, base_url = get_agent_credentials(resolved_agent)
    model_name = get_agent_model(resolved_agent)
    if not api_key or not base_url or not model_name:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="模型未配置")

    is_guest = current_user is None
    if not is_guest and payload.conversation_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conversation_id is required")

    user_message_id = None
    if not is_guest:
        convo = _get_conversation(db, payload.conversation_id, current_user.id, resolved_agent)
        user_message = _add_message(db, convo.id, "user", messages[-1]["content"], current_user.id)
        user_message_id = user_message.id
        memory_summary = fetch_latest_memory_summary(db, current_user.id, resolved_agent)
    else:
        convo = None
        memory_summary = None

    profile = get_agent_profile(resolved_agent)
    profile_id = profile.get("id") if profile else None
    profile_version = profile.get("version") if profile else None
    if profile:
        write_agent_log(
            {
                "event": "agent_profile",
                "agent": resolved_agent,
                "conversation_id": convo.id if convo else None,
                "user_id": current_user.id if current_user else None,
                "profile_id": profile_id,
                "profile_version": profile_version,
                "allow_tools": sorted(list(profile.get("allow_tools", []))),
                "scope": profile.get("scope"),
            }
        )
    messages_with_hint = _build_selected_hint(messages, selected_messages)
    messages_to_model = _attach_memory_prompt(
        messages_with_hint,
        memory_summary,
        agent_config.get("title", resolved_agent),
        resolved_agent,
        current_user.id if current_user else None,
    )
    system_message = None
    if messages_to_model and messages_to_model[0].get("role") == "system":
        system_message = messages_to_model[0]
    trace_seed: list[dict[str, Any]] = [
        {
            "type": "context",
            "source": "request",
            "agent": resolved_agent,
            "profile_id": profile_id,
            "profile_version": profile_version,
            "user_id": current_user.id if current_user else None,
            "conversation_id": convo.id if convo else None,
            "user_message_id": user_message_id,
        }
    ]
    if routing_decision:
        trace_seed.append(
            {
                "type": "routing_decision",
                "source": "router",
                "decision": routing_decision,
            }
        )
    if messages:
        trace_seed.append(
            {
                "type": "user_message",
                "source": "user",
                "content": messages[-1]["content"],
                "message_id": user_message_id,
            }
        )
    if selected_messages:
        trace_seed.append(
            {
                "type": "selected_messages",
                "source": "user",
                "messages": selected_messages,
            }
        )
    if system_message:
        trace_seed.append(
            {
                "type": "system_prompt",
                "source": "agent_prompts",
                "content": system_message.get("content", ""),
                "template_path": PROMPT_TEMPLATE_PATH,
                "agent": resolved_agent,
            }
        )
    if memory_summary:
        trace_seed.append(
            {
                "type": "memory_summary",
                "source": "memory",
                "content": memory_summary,
            }
        )
    trace_seed.append(
        {
            "type": "assembled_messages",
            "source": "orchestrator",
            "messages": messages_to_model,
        }
    )

    def event_generator():
        start_time = time.monotonic()
        assistant_chunks: list[str] = []
        assistant_message_id = None
        stream_completed = False
        convo_id = convo.id if convo else None
        user_id = current_user.id if current_user else None
        plan_json = None
        tool_summary = None
        final_text: str | None = None
        trace_events: list[dict[str, Any]] = []

        def add_trace(event: dict[str, Any]) -> None:
            event["seq"] = len(trace_events) + 1
            trace_events.append(event)

        for seed in trace_seed:
            add_trace(dict(seed))

        def emit_chunk(chunk: str, stream_db: Session | None = None) -> str:
            nonlocal assistant_message_id
            assistant_chunks.append(chunk)
            full_text = "".join(assistant_chunks)
            if stream_db and convo:
                if assistant_message_id is None:
                    message = _add_message(stream_db, convo.id, "assistant", full_text, None)
                    assistant_message_id = message.id
                else:
                    stream_db.query(Message).filter(Message.id == assistant_message_id).update(
                        {Message.content: full_text}
                    )
                    stream_db.query(Conversation).filter(Conversation.id == convo.id).update(
                        {Conversation.updated_at: datetime.utcnow()}
                    )
                    stream_db.commit()
            return f"data: {json.dumps({'content': chunk})}\n\n"

        with SessionLocal() as stream_db:
            try:
                registry = load_tool_registry(stream_db)
                allowed_tools = get_agent_allowed_tools_from_profile(resolved_agent) or get_agent_allowed_tools(
                    resolved_agent
                )
                if allowed_tools:
                    registry = registry.__class__(
                        {name: definition for name, definition in registry.tools.items() if name in allowed_tools}
                    )
                tools_payload = registry.to_openai_tools()
                messages_for_round = messages_to_model
                tool_calls: list[dict] = []
                raw_tool_calls: list[dict] = []
                used_json_fallback = False
                assistant_content = ""

                if tools_payload:
                    add_trace(
                        {
                            "type": "llm_request",
                            "stage": "planning",
                            "source": "orchestrator",
                            "model": model_name,
                            "messages": messages_for_round,
                            "tools": tools_payload,
                        }
                    )
                    assistant_content, tool_calls, raw_tool_calls, used_json_fallback, plan_json = plan_with_tools(
                        messages_for_round,
                        tools_payload,
                        model_name,
                        api_key,
                        base_url,
                        registry,
                        resolved_agent,
                        user_id,
                        convo_id,
                    )
                    add_trace(
                        {
                            "type": "llm_response",
                            "stage": "planning",
                            "source": "llm",
                            "assistant_content": assistant_content,
                            "tool_calls": tool_calls,
                            "raw_tool_calls": raw_tool_calls,
                            "json_fallback": used_json_fallback,
                            "plan": plan_json,
                        }
                    )
                else:
                    add_trace(
                        {
                            "type": "llm_request",
                            "stage": "direct",
                            "source": "orchestrator",
                            "model": model_name,
                            "messages": messages_for_round,
                            "tools": [],
                        }
                    )

                missing_slots = identify_missing_slots(tool_calls, registry)
                if missing_slots:
                    write_agent_log(
                        {
                            "event": "missing_slots",
                            "agent": resolved_agent,
                            "conversation_id": convo_id,
                            "user_id": user_id,
                            "missing_slots": missing_slots,
                        }
                    )
                    clarify_text = build_missing_slots_question(missing_slots)
                    add_trace(
                        {
                            "type": "missing_slots",
                            "source": "orchestrator",
                            "missing_slots": missing_slots,
                            "clarify_text": clarify_text,
                        }
                    )
                    add_trace(
                        {
                            "type": "final_response",
                            "source": "orchestrator",
                            "content": clarify_text,
                        }
                    )
                    final_text = clarify_text
                    chunk_iter = [clarify_text]
                elif tool_calls:
                    tool_results, tool_summary = execute_plan(
                        tool_calls, registry, stream_db, resolved_agent, user_id, convo_id
                    )
                    add_trace(
                        {
                            "type": "tool_results",
                            "source": "tool_executor",
                            "results": tool_results,
                            "summary": tool_summary,
                        }
                    )
                    assistant_message, tool_messages = _build_tool_messages(
                        tool_calls, tool_results, assistant_content
                    )
                    final_messages = messages_for_round + [assistant_message] + tool_messages
                    final_messages.append({"role": "system", "content": FINAL_TOOL_INSTRUCTION})
                    add_trace(
                        {
                            "type": "llm_request",
                            "stage": "synthesis",
                            "source": "orchestrator",
                            "model": model_name,
                            "messages": final_messages,
                            "tools": [],
                        }
                    )
                    final_text = synthesize_with_tools(
                        messages_for_round,
                        assistant_content,
                        tool_calls,
                        tool_results,
                        model_name,
                        api_key,
                        base_url,
                        resolved_agent,
                    )
                    add_trace(
                        {
                            "type": "llm_response",
                            "stage": "synthesis",
                            "source": "llm",
                            "content": final_text,
                        }
                    )
                    chunk_iter = [final_text] if final_text else []
                else:
                    if assistant_content:
                        final_text = assistant_content
                        add_trace(
                            {
                                "type": "llm_response",
                                "stage": "planning",
                                "source": "llm",
                                "assistant_content": assistant_content,
                                "note": "no_tool_calls",
                            }
                        )
                        chunk_iter = [assistant_content]
                    else:
                        chunk_iter = stream_without_tools(
                            model_name, messages_for_round, api_key=api_key, base_url=base_url
                        )

                sent_any = False
                for chunk in chunk_iter:
                    if not chunk:
                        continue
                    sent_any = True
                    if is_guest:
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                    else:
                        yield emit_chunk(chunk, stream_db)
                if final_text is None and assistant_chunks:
                    final_text = "".join(assistant_chunks)
                    add_trace(
                        {
                            "type": "llm_response",
                            "stage": "direct",
                            "source": "llm",
                            "content": final_text,
                        }
                    )
                if sent_any:
                    stream_completed = True
                if not stream_completed:
                    yield f"data: {json.dumps({'error': 'tool_call_loop'})}\n\n"
            except Exception:
                logger.exception("Chat stream failed")
                add_trace(
                    {
                        "type": "error",
                        "source": "orchestrator",
                        "message": "chat_stream_failed",
                    }
                )
                yield f"data: {json.dumps({'error': 'service unavailable'})}\n\n"

            # Trigger memory summarization after successful completion
            if stream_completed and not is_guest:
                try:
                    final_answer = final_text or ("".join(assistant_chunks) if assistant_chunks else None)
                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    agent_run_id = write_agent_run(
                        stream_db,
                        {
                            "agent": resolved_agent,
                            "user_id": user_id,
                            "conversation_id": convo_id,
                            "profile_id": profile_id,
                            "profile_version": profile_version,
                            "request_text": messages[-1]["content"] if messages else None,
                            "plan_json": plan_json,
                            "tool_summary": tool_summary,
                            "final_answer": final_answer,
                            "latency_ms": latency_ms,
                            "cost": None,
                        },
                    )
                    write_agent_run_trace(
                        stream_db,
                        {
                            "agent_run_id": agent_run_id,
                            "agent": resolved_agent,
                            "user_id": user_id,
                            "conversation_id": convo_id,
                            "user_message_id": user_message_id,
                            "request_text": messages[-1]["content"] if messages else None,
                            "trace": trace_events,
                        },
                    )
                except Exception:
                    logger.exception("Agent run logging failed (non-blocking)")

                try:
                    generate_memory_summary(stream_db, current_user.id, resolved_agent)
                except Exception:
                    logger.exception("Memory summarization failed (non-blocking)")

                try:
                    generate_conversation_title(stream_db, convo.id)
                except Exception:
                    logger.exception("Conversation title generation failed (non-blocking)")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
