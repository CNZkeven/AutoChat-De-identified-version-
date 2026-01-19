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
from ..services.agent_prompts import get_agent_allowed_tools, get_agent_system_prompt
from ..services.ai import call_ai_model, call_ai_model_stream, call_ai_model_with_tools
from ..services.memory import fetch_latest_memory_summary, generate_memory_summary
from ..services.title import generate_conversation_title
from ..services.tool_executor import execute_tool_calls
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


def _build_tool_messages(
    tool_calls: list[dict],
    tool_results: list[dict],
    assistant_content: str,
) -> tuple[dict, list[dict]]:
    tool_call_payload = []
    for index, call in enumerate(tool_calls, start=1):
        call_id = call.get("id") or f"json-fallback-{index}"
        tool_call_payload.append(
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": call.get("name"),
                    "arguments": json.dumps(call.get("args", {}), ensure_ascii=False),
                },
            }
        )
        call["id"] = call_id
    assistant_message = {
        "role": "assistant",
        "content": assistant_content or "",
        "tool_calls": tool_call_payload,
    }
    tool_messages = []
    for index, result in enumerate(tool_results, start=1):
        tool_call_id = result.get("id") or f"json-fallback-{index}"
        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result.get("result", {}), ensure_ascii=False),
            }
        )
    return assistant_message, tool_messages


def _extract_json_payload(content: str) -> str | None:
    if not content:
        return None
    trimmed = content.strip()
    if trimmed.startswith("{") or trimmed.startswith("["):
        return trimmed
    if "```" not in content:
        return None
    parts = content.split("```")
    if len(parts) < 3:
        return None
    candidate = parts[1]
    if "\n" in candidate:
        candidate = candidate.split("\n", 1)[1]
    return candidate.strip()


def _parse_json_tool_calls(content: str) -> list[dict]:
    payload = _extract_json_payload(content)
    if not payload:
        return []
    try:
        data = json.loads(payload)
    except Exception:
        return []
    calls: list[dict] = []
    if isinstance(data, dict):
        if "tool" in data and "args" in data:
            calls.append({"id": None, "name": data.get("tool"), "args": data.get("args", {})})
        if isinstance(data.get("tool_calls"), list):
            for item in data["tool_calls"]:
                if isinstance(item, dict) and "tool" in item and "args" in item:
                    calls.append(
                        {"id": item.get("id"), "name": item.get("tool"), "args": item.get("args", {})}
                    )
        return calls
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "tool" in item and "args" in item:
                calls.append({"id": item.get("id"), "name": item.get("tool"), "args": item.get("args", {})})
    return calls


def _augment_tool_calls(agent: str, messages: list[dict], tool_calls: list[dict]) -> list[dict]:
    if agent != "ideological":
        return tool_calls
    last_user = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user = msg.get("content", "")
            break
    has_search = any(call.get("name") == "search_knowledge_repository" for call in tool_calls)
    if has_search or not last_user:
        return tool_calls
    keywords = last_user.strip()[:80]
    augmented = list(tool_calls)
    augmented.append(
        {
            "id": None,
            "name": "search_knowledge_repository",
            "args": {"source": "internal_kb", "query_type": "tech_evolution", "keywords": keywords},
        }
    )
    augmented.append(
        {
            "id": None,
            "name": "search_knowledge_repository",
            "args": {"source": "internal_kb", "query_type": "spirit_genealogy", "keywords": keywords},
        }
    )
    if any(key in last_user for key in ["工程", "项目", "航母", "LNG", "大国重器"]):
        augmented.append(
            {
                "id": None,
                "name": "search_knowledge_repository",
                "args": {"source": "internal_kb", "query_type": "engineering_projects", "keywords": keywords},
            }
        )
    return augmented


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
    agent_config = AGENT_CONFIG.get(agent)
    if not agent_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")

    api_key, base_url = get_agent_credentials(agent)
    model_name = get_agent_model(agent)
    if not api_key or not base_url or not model_name:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="模型未配置")

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
        _add_message(db, convo.id, "user", messages[-1]["content"], current_user.id)
        memory_summary = fetch_latest_memory_summary(db, current_user.id, agent)
    else:
        convo = None
        memory_summary = None
    messages_with_hint = _build_selected_hint(messages, selected_messages)
    messages_to_model = _attach_memory_prompt(
        messages_with_hint,
        memory_summary,
        agent_config.get("title", agent),
        agent,
        current_user.id if current_user else None,
    )

    def event_generator():
        assistant_chunks: list[str] = []
        assistant_message_id = None
        stream_completed = False
        convo_id = convo.id if convo else None
        user_id = current_user.id if current_user else None

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
                allowed_tools = get_agent_allowed_tools(agent)
                if allowed_tools:
                    registry = registry.__class__(
                        {name: definition for name, definition in registry.tools.items() if name in allowed_tools}
                    )
                tools_payload = registry.to_openai_tools()
                messages_for_round = messages_to_model
                tool_calls: list[dict] = []
                raw_tool_calls: list[dict] = []
                assistant_content = ""
                used_json_fallback = False

                if tools_payload:
                    assistant_content, tool_calls, raw_tool_calls = call_ai_model_with_tools(
                        model_name,
                        messages_for_round,
                        api_key=api_key,
                        base_url=base_url,
                        tools=tools_payload,
                    )
                    if not tool_calls and assistant_content:
                        tool_calls = _parse_json_tool_calls(assistant_content)
                        used_json_fallback = bool(tool_calls)

                    tool_calls = _augment_tool_calls(agent, messages_for_round, tool_calls)

                    write_agent_log(
                        {
                            "event": "tool_decision",
                            "agent": agent,
                            "conversation_id": convo_id,
                            "user_id": user_id,
                            "tool_calls": raw_tool_calls,
                            "assistant_content": assistant_content,
                            "json_fallback": used_json_fallback,
                        }
                    )

                if tool_calls:
                    tool_results = execute_tool_calls(
                        tool_calls, registry, stream_db, agent, user_id, convo_id
                    )
                    assistant_message, tool_messages = _build_tool_messages(
                        tool_calls, tool_results, assistant_content
                    )
                    final_messages = messages_for_round + [assistant_message] + tool_messages
                    final_messages.append(
                        {
                            "role": "system",
                            "content": "工具结果已提供，请基于工具结果给出最终回复，禁止再调用工具或输出工具调用格式。",
                        }
                    )
                    final_text = call_ai_model(
                        model_name, final_messages, api_key=api_key, base_url=base_url
                    )
                    if "<tool_call>" in final_text or "\"tool\"" in final_text:
                        final_messages.append(
                            {
                                "role": "system",
                                "content": "再次强调：直接给出最终回复，不要输出任何工具调用。",
                            }
                        )
                        final_text = call_ai_model(
                            model_name, final_messages, api_key=api_key, base_url=base_url
                        )
                    chunk_iter = [final_text] if final_text else []
                else:
                    chunk_iter = [assistant_content] if assistant_content else call_ai_model_stream(
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
                if sent_any:
                    stream_completed = True
                if not stream_completed:
                    yield f"data: {json.dumps({'error': 'tool_call_loop'})}\n\n"
            except Exception:
                logger.exception("Chat stream failed")
                yield f"data: {json.dumps({'error': 'service unavailable'})}\n\n"

            # Trigger memory summarization after successful completion
            if stream_completed and not is_guest:
                try:
                    generate_memory_summary(stream_db, current_user.id, agent)
                except Exception:
                    logger.exception("Memory summarization failed (non-blocking)")

                try:
                    generate_conversation_title(stream_db, convo.id)
                except Exception:
                    logger.exception("Conversation title generation failed (non-blocking)")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
