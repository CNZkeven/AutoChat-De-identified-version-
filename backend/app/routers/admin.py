import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_agent_credentials, get_agent_model
from ..db import get_db
from ..deps import get_admin_user
from ..models import AgentRunTrace, Conversation, Message, User, UserProfile
from ..schemas import (
    AdminAgentOut,
    AdminConversationOut,
    AdminDebugRunRequest,
    AdminDebugRunResponse,
    AdminRunDetailOut,
    AdminRunSummaryOut,
    AdminUserOut,
    AdminUserProfileOut,
)
from ..services.agent_profiles import get_agent_allowed_tools_from_profile, get_agent_profile
from ..services.agent_prompts import get_agent_allowed_tools, get_agent_system_prompt
from ..services.agent_router import resolve_agent
from ..services.agent_run_logger import write_agent_run, write_agent_run_trace
from ..services.ai import call_ai_model
from ..services.memory import fetch_latest_memory_summary, generate_memory_summary
from ..services.orchestrator import (
    FINAL_TOOL_INSTRUCTION,
    _build_tool_messages,
    build_missing_slots_question,
    execute_plan,
    identify_missing_slots,
    plan_with_tools,
    synthesize_with_tools,
)
from ..services.title import generate_conversation_title
from ..services.tool_registry import load_tool_registry
from .chat import (
    AGENT_CONFIG,
    PROMPT_TEMPLATE_PATH,
    _attach_memory_prompt,
    _build_selected_hint,
    _validate_messages,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


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


@router.get("/me", response_model=AdminUserOut)
def admin_me(admin_user: User = Depends(get_admin_user)) -> User:
    return admin_user


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    q: str | None = Query(default=None, max_length=64),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> list[User]:
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter(User.username.ilike(like))
    return query.order_by(User.id.asc()).limit(200).all()


@router.get("/users/{user_id}/profile", response_model=AdminUserProfileOut)
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> AdminUserProfileOut:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    return AdminUserProfileOut(user_id=user_id, data=profile.data if profile else {})


@router.get("/agents", response_model=list[AdminAgentOut])
def list_agents(admin_user: User = Depends(get_admin_user)) -> list[AdminAgentOut]:
    agents: list[AdminAgentOut] = []
    for agent_id, config in AGENT_CONFIG.items():
        profile = get_agent_profile(agent_id)
        agents.append(
            AdminAgentOut(
                id=agent_id,
                title=config.get("title", agent_id),
                greeting=config.get("greeting"),
                profile=profile,
                prompt=get_agent_system_prompt(agent_id),
                prompt_template_path=PROMPT_TEMPLATE_PATH,
            )
        )
    return agents


@router.get(
    "/users/{user_id}/agents/{agent}/conversations",
    response_model=list[AdminConversationOut],
)
def list_conversations_for_agent(
    user_id: int,
    agent: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> list[Conversation]:
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.agent == agent)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return rows


@router.get("/conversations/{conversation_id}/runs", response_model=list[AdminRunSummaryOut])
def list_conversation_runs(
    conversation_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> list[AgentRunTrace]:
    rows = (
        db.query(AgentRunTrace)
        .filter(AgentRunTrace.conversation_id == conversation_id)
        .order_by(AgentRunTrace.created_at.asc())
        .all()
    )
    return rows


@router.get("/runs/{trace_id}", response_model=AdminRunDetailOut)
def get_run_trace(
    trace_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> AgentRunTrace:
    trace = db.query(AgentRunTrace).filter(AgentRunTrace.id == trace_id).first()
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    return trace


@router.post("/debug/run", response_model=AdminDebugRunResponse)
def debug_run(
    payload: AdminDebugRunRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> AdminDebugRunResponse:
    start_time = time.monotonic()
    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    messages = _validate_messages(payload.messages, "messages")
    selected_messages = _validate_messages(payload.selected_messages, "selected_messages")
    if not messages and payload.message:
        messages = [{"role": "user", "content": payload.message.strip()}]

    if not messages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one message required")

    if messages[-1]["role"] != "user":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Last message must be from user")

    resolved_agent = payload.agent
    routing_decision: dict[str, Any] | None = None
    if resolved_agent in {"auto", "router"}:
        last_user_content = messages[-1]["content"]
        routing_decision = resolve_agent(
            last_user_content,
            list(AGENT_CONFIG.keys()),
            default_agent="ideological",
        )
        resolved_agent = routing_decision.get("agent_id", "ideological")

    agent_config = AGENT_CONFIG.get(resolved_agent)
    if not agent_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")

    api_key, base_url = get_agent_credentials(resolved_agent)
    model_name = get_agent_model(resolved_agent)
    if not api_key or not base_url or not model_name:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="模型未配置")

    if payload.conversation_id is not None:
        convo = _get_conversation(db, payload.conversation_id, target_user.id, resolved_agent)
    else:
        title = (payload.message or "调试对话").strip() or "调试对话"
        convo = Conversation(
            user_id=target_user.id,
            title=title,
            agent=resolved_agent,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(convo)
        db.commit()
        db.refresh(convo)

    user_message = _add_message(db, convo.id, "user", messages[-1]["content"], target_user.id)
    memory_summary = fetch_latest_memory_summary(db, target_user.id, resolved_agent)

    profile = get_agent_profile(resolved_agent)
    profile_id = profile.get("id") if profile else None
    profile_version = profile.get("version") if profile else None

    messages_with_hint = _build_selected_hint(messages, selected_messages)
    messages_to_model = _attach_memory_prompt(
        messages_with_hint,
        memory_summary,
        agent_config.get("title", resolved_agent),
        resolved_agent,
        target_user.id,
    )

    system_message = None
    if messages_to_model and messages_to_model[0].get("role") == "system":
        system_message = messages_to_model[0]

    trace_events: list[dict[str, Any]] = []

    def add_trace(event: dict[str, Any]) -> None:
        event["seq"] = len(trace_events) + 1
        trace_events.append(event)

    add_trace(
        {
            "type": "context",
            "source": "request",
            "agent": resolved_agent,
            "style": payload.style,
            "profile_id": profile_id,
            "profile_version": profile_version,
            "user_id": target_user.id,
            "conversation_id": convo.id,
            "user_message_id": user_message.id,
        }
    )
    if routing_decision:
        add_trace(
            {
                "type": "routing_decision",
                "source": "router",
                "decision": routing_decision,
            }
        )
    add_trace(
        {
            "type": "user_message",
            "source": "user",
            "content": messages[-1]["content"],
            "message_id": user_message.id,
        }
    )
    if selected_messages:
        add_trace(
            {
                "type": "selected_messages",
                "source": "user",
                "messages": selected_messages,
            }
        )
    if system_message:
        add_trace(
            {
                "type": "system_prompt",
                "source": "agent_prompts",
                "content": system_message.get("content", ""),
                "template_path": PROMPT_TEMPLATE_PATH,
                "agent": resolved_agent,
            }
        )
    if memory_summary:
        add_trace(
            {
                "type": "memory_summary",
                "source": "memory",
                "content": memory_summary,
            }
        )
    add_trace(
        {
            "type": "assembled_messages",
            "source": "orchestrator",
            "messages": messages_to_model,
        }
    )

    registry = load_tool_registry(db)
    allowed_tools = get_agent_allowed_tools_from_profile(resolved_agent) or get_agent_allowed_tools(resolved_agent)
    if allowed_tools:
        registry = registry.__class__(
            {name: definition for name, definition in registry.tools.items() if name in allowed_tools}
        )
    tools_payload = registry.to_openai_tools()
    messages_for_round = messages_to_model

    assistant_content = ""
    tool_calls: list[dict[str, Any]] = []
    raw_tool_calls: list[dict[str, Any]] = []
    used_json_fallback = False
    plan_json = None
    tool_summary = None
    final_text: str | None = None

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
            target_user.id,
            convo.id,
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
    elif tool_calls:
        tool_results, tool_summary = execute_plan(
            tool_calls, registry, db, resolved_agent, target_user.id, convo.id
        )
        add_trace(
            {
                "type": "tool_results",
                "source": "tool_executor",
                "results": tool_results,
                "summary": tool_summary,
            }
        )
        assistant_message, tool_messages = _build_tool_messages(tool_calls, tool_results, assistant_content)
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
        else:
            final_text = call_ai_model(
                model_name,
                messages_for_round,
                api_key=api_key,
                base_url=base_url,
            )
            add_trace(
                {
                    "type": "llm_response",
                    "stage": "direct",
                    "source": "llm",
                    "content": final_text,
                }
            )

    _add_message(db, convo.id, "assistant", final_text or "", None)

    latency_ms = int((time.monotonic() - start_time) * 1000)
    agent_run_id = write_agent_run(
        db,
        {
            "agent": resolved_agent,
            "user_id": target_user.id,
            "conversation_id": convo.id,
            "profile_id": profile_id,
            "profile_version": profile_version,
            "request_text": messages[-1]["content"],
            "plan_json": plan_json,
            "tool_summary": tool_summary,
            "final_answer": final_text,
            "latency_ms": latency_ms,
            "cost": None,
        },
    )
    trace_id = write_agent_run_trace(
        db,
        {
            "agent_run_id": agent_run_id,
            "agent": resolved_agent,
            "user_id": target_user.id,
            "conversation_id": convo.id,
            "user_message_id": user_message.id,
            "request_text": messages[-1]["content"],
            "trace": trace_events,
        },
    )

    try:
        generate_memory_summary(db, target_user.id, resolved_agent)
    except Exception:
        pass

    try:
        generate_conversation_title(db, convo.id)
    except Exception:
        pass

    return AdminDebugRunResponse(
        conversation_id=convo.id,
        trace_id=trace_id,
        final_text=final_text,
    )
