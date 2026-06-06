import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from .ai import call_ai_model, call_ai_model_stream, call_ai_model_with_tools
from .tool_executor import execute_tool_calls
from .tool_logging import write_agent_log
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


FINAL_TOOL_INSTRUCTION = "工具结果已提供，请基于工具结果给出最终回复，禁止再调用工具或输出工具调用格式。"
RETRY_TOOL_LEAK_INSTRUCTION = "再次强调：直接给出最终回复，不要输出任何工具调用。"
DIRECT_NO_TOOL_INSTRUCTION = (
    "当前工具通道不可用，不能调用工具。请直接面向用户作答；"
    "如缺少内部数据，请说明暂无可用数据。禁止输出 JSON、<tool_call> 或任何工具调用格式。"
)
FALLBACK_MESSAGE = "模型服务暂时不可用，请稍后再试。"
SYNTHESIS_MAX_TOKENS = 4096
STREAM_GUARD_BUFFER_LIMIT = 512


def _extract_last_user_message(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "") or ""
    return ""


def _tool_results_have_course_data(tool_results: list[dict[str, Any]]) -> bool:
    for result in tool_results:
        payload = result.get("result", {})
        if not isinstance(payload, dict):
            continue
        if payload.get("status") != "ok":
            continue
        name = result.get("name")
        if name == "query_institutional_database":
            results = payload.get("results")
            if isinstance(results, list) and results:
                return True
    return False


def _build_course_no_data_response(user_content: str) -> str:
    content = user_content or ""
    header = (
        "目前课程库/知识库/学生画像未返回可用数据，无法提供具体课程名称、学分、开课学期或先修课信息。"
    )
    if any(keyword in content for keyword in ["复习", "期末", "安排", "备考", "冲刺"]):
        body = (
            "如果需要通用复习建议：先梳理课程知识框架，再用作业/真题定位薄弱点，集中补齐核心概念，"
            "每轮复习后做小结并迭代。若需更贴合课程内容，请提供课程代码或教学大纲。"
        )
    elif any(keyword in content for keyword in ["难吗", "难不难", "主要学什么", "内容", "重点"]):
        body = (
            "建议先获取课程大纲或教学计划，我可以据此梳理知识结构与学习重点。"
            "请提供课程代码、学院或培养方案版本。"
        )
    elif any(keyword in content for keyword in ["学分", "毕业", "要求", "够不够"]):
        body = "需要培养方案中的毕业学分要求与已修清单，请提供后我可帮你核对是否满足要求。"
    elif any(keyword in content for keyword in ["先修", "先修课", "前置"]):
        body = "需要课程大纲或培养方案中的先修关系，请提供课程代码或课程名称以便查询。"
    elif any(keyword in content for keyword in ["选课", "推荐", "选修", "建议选", "修读"]):
        body = (
            "请补充专业、年级、培养方案版本、兴趣方向与已修课程，我可以基于培养方案与大纲给出匹配建议。"
            "在缺少数据时我不会推荐具体课程。"
        )
    else:
        body = "请补充专业、年级、课程名称/代码或培养方案版本，我可以据此查询并给出具体解答。"
    return f"{header}\n{body}"


def _build_tool_messages(
    tool_calls: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    assistant_content: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
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
                "content": json.dumps(result.get("result", {}), ensure_ascii=False, default=str),
            }
        )
    return assistant_message, tool_messages


def _build_synthesis_messages(
    messages: list[dict[str, Any]],
    assistant_content: str,
    tool_calls: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    assistant_message, tool_messages = _build_tool_messages(tool_calls, tool_results, assistant_content)
    final_messages = messages + [assistant_message] + tool_messages
    final_messages.append({"role": "system", "content": FINAL_TOOL_INSTRUCTION})
    return final_messages


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


def _coerce_tool_args(args: Any) -> dict[str, Any]:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except Exception:
            return {"_raw": args}
        return parsed if isinstance(parsed, dict) else {"_raw": args}
    return {"_raw": args}


def _collect_json_tool_calls(data: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def append_call(item: Any) -> None:
        if not isinstance(item, dict):
            return
        if "tool" in item and "args" in item:
            calls.append(
                {
                    "id": item.get("id"),
                    "name": item.get("tool"),
                    "args": _coerce_tool_args(item.get("args", {})),
                }
            )
            return
        function = item.get("function")
        if isinstance(function, dict) and function.get("name"):
            calls.append(
                {
                    "id": item.get("id"),
                    "name": function.get("name"),
                    "args": _coerce_tool_args(function.get("arguments", {})),
                }
            )
            return
        if "name" in item and "arguments" in item:
            calls.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "args": _coerce_tool_args(item.get("arguments", {})),
                }
            )

    if isinstance(data, dict):
        append_call(data)
        if isinstance(data.get("tool_calls"), list):
            for item in data["tool_calls"]:
                append_call(item)
    elif isinstance(data, list):
        for item in data:
            append_call(item)
    return calls


def _parse_json_values(payload: str) -> list[Any]:
    try:
        return [json.loads(payload)]
    except Exception:
        pass

    decoder = json.JSONDecoder()
    values: list[Any] = []
    index = 0
    length = len(payload)
    while index < length:
        while index < length and payload[index].isspace():
            index += 1
        if index >= length:
            break
        if payload[index] not in "{[":
            return []
        try:
            value, index = decoder.raw_decode(payload, index)
        except Exception:
            return []
        values.append(value)
    return values


def _parse_json_tool_calls(content: str) -> list[dict[str, Any]]:
    payload = _extract_json_payload(content)
    if not payload:
        return []
    calls: list[dict[str, Any]] = []
    for value in _parse_json_values(payload):
        calls.extend(_collect_json_tool_calls(value))
    return calls


def _looks_like_tool_call_leak(content: str) -> bool:
    if not content:
        return False
    if "<tool_call>" in content or "</tool_call>" in content:
        return True
    if _parse_json_tool_calls(content):
        return True
    return '"tool"' in content and '"args"' in content


def _should_hold_stream_buffer(content: str) -> bool:
    stripped = content.lstrip()
    if not stripped:
        return True
    if len(content) >= STREAM_GUARD_BUFFER_LIMIT:
        return False
    return stripped.startswith(("{", "[", "<", "```"))


def _retry_after_tool_leak(
    model_name: str,
    messages: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    log_entry: dict[str, Any],
) -> list[str]:
    retry_messages = messages + [{"role": "system", "content": RETRY_TOOL_LEAK_INSTRUCTION}]
    retry_text = call_ai_model(
        model_name,
        retry_messages,
        api_key=api_key,
        base_url=base_url,
        max_tokens=SYNTHESIS_MAX_TOKENS,
    )
    if _looks_like_tool_call_leak(retry_text):
        write_agent_log(log_entry)
        return [FALLBACK_MESSAGE]
    return [retry_text] if retry_text else [FALLBACK_MESSAGE]


def _stream_with_tool_leak_guard(
    model_name: str,
    messages: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    log_entry: dict[str, Any],
) -> Any:
    pending = ""
    released = False
    for chunk in call_ai_model_stream(
        model_name,
        messages,
        api_key=api_key,
        base_url=base_url,
        max_tokens=SYNTHESIS_MAX_TOKENS,
    ):
        if not chunk:
            continue
        if released:
            yield chunk
            continue
        pending += chunk
        if _looks_like_tool_call_leak(pending):
            for retry_chunk in _retry_after_tool_leak(model_name, messages, api_key, base_url, log_entry):
                yield retry_chunk
            return
        if _should_hold_stream_buffer(pending):
            continue
        released = True
        yield pending

    if pending and not released:
        if _looks_like_tool_call_leak(pending):
            for retry_chunk in _retry_after_tool_leak(model_name, messages, api_key, base_url, log_entry):
                yield retry_chunk
        else:
            yield pending


def _augment_tool_calls(agent: str, messages: list[dict[str, Any]], tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if agent != "ideological":
        if agent not in {"evaluation", "task", "exploration", "competition", "course"}:
            return tool_calls
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg.get("content", "")
                break
        if not last_user:
            return tool_calls
        augmented = list(tool_calls)
        has_profile = any(call.get("name") == "get_user_comprehensive_profile" for call in augmented)
        if agent == "evaluation":
            has_error = any(
                call.get("name") == "execute_strategy_engine"
                and call.get("args", {}).get("action") == "check_error_book"
                for call in augmented
            )
            is_assignment = any(key in last_user for key in ["作业", "报告", "批改", "实验报告"])
            if is_assignment and not has_error:
                augmented.append(
                    {
                        "id": None,
                        "name": "execute_strategy_engine",
                        "args": {
                            "action": "check_error_book",
                            "context_data": {"note": "assignment_review"},
                        },
                    }
                )
            if not has_profile:
                augmented.append(
                    {
                        "id": None,
                        "name": "get_user_comprehensive_profile",
                        "args": {"user_id": "default", "scope": "basic"},
                    }
                )
            return augmented
        if agent == "task":
            has_plan = any(
                call.get("name") == "execute_strategy_engine"
                and call.get("args", {}).get("action") in {"generate_plan", "log_milestone"}
                for call in augmented
            )
            has_curriculum = any(
                call.get("name") == "query_institutional_database"
                and call.get("args", {}).get("category") == "curriculum"
                for call in augmented
            )
            wants_progress = any(key in last_user for key in ["完成", "已做", "已完成", "打卡", "进度"])
            wants_plan = any(key in last_user for key in ["任务", "计划", "安排", "待办", "截止", "提醒"])
            mentions_course = any(key in last_user for key in ["课程", "课程设计", "教学", "考试", "学分", "作业"])
            if (wants_plan or wants_progress) and not has_plan:
                action = "log_milestone" if wants_progress and not wants_plan else "generate_plan"
                augmented.append(
                    {
                        "id": None,
                        "name": "execute_strategy_engine",
                        "args": {
                            "action": action,
                            "context_data": {"note": "task_flow", "request": last_user[:200]},
                        },
                    }
                )
            if mentions_course and not has_curriculum:
                augmented.append(
                    {
                        "id": None,
                        "name": "query_institutional_database",
                        "args": {"category": "curriculum", "keywords": last_user[:60]},
                    }
                )
            if not has_profile:
                augmented.append(
                    {
                        "id": None,
                        "name": "get_user_comprehensive_profile",
                        "args": {"user_id": "default", "scope": "basic"},
                    }
                )
            return augmented
        if agent == "exploration":
            has_search = any(call.get("name") == "search_knowledge_repository" for call in augmented)
            needs_search = any(
                key in last_user for key in ["是什么", "原理", "机制", "概念", "区别", "为什么", "如何", "怎么"]
            )
            if needs_search and not has_search:
                augmented.append(
                    {
                        "id": None,
                        "name": "search_knowledge_repository",
                        "args": {
                            "source": "internal_kb",
                            "query_type": "tech_evolution",
                            "keywords": last_user[:80],
                        },
                    }
                )
            if not has_profile:
                augmented.append(
                    {
                        "id": None,
                        "name": "get_user_comprehensive_profile",
                        "args": {"user_id": "default", "scope": "basic"},
                    }
                )
            return augmented
        if agent == "competition":
            has_history = any(
                call.get("name") == "query_institutional_database"
                and call.get("args", {}).get("category") == "competition_history"
                for call in augmented
            )
            has_competition_info = any(
                call.get("name") == "search_knowledge_repository"
                and call.get("args", {}).get("query_type") == "competition_info"
                for call in augmented
            )
            has_skill = any(
                call.get("name") == "search_knowledge_repository"
                and call.get("args", {}).get("query_type") == "skill_inference"
                for call in augmented
            )
            has_advisor = any(
                call.get("name") == "execute_strategy_engine"
                and call.get("args", {}).get("action") == "recommend_advisor"
                for call in augmented
            )
            has_team = any(
                call.get("name") == "execute_strategy_engine"
                and call.get("args", {}).get("action") == "analyze_team_model"
                for call in augmented
            )
            mentions_competition = any(key in last_user for key in ["竞赛", "比赛", "挑战杯", "创青春", "互联网+", "机器人", "国赛"])
            asks_skills = any(key in last_user for key in ["学什么", "技能", "准备", "技术栈", "能力"])
            asks_advisor = any(key in last_user for key in ["导师", "老师", "指导", "组队", "队伍"])

            if mentions_competition and not has_history:
                augmented.append(
                    {
                        "id": None,
                        "name": "query_institutional_database",
                        "args": {"category": "competition_history", "keywords": last_user[:60]},
                    }
                )
            if mentions_competition and not has_competition_info:
                augmented.append(
                    {
                        "id": None,
                        "name": "search_knowledge_repository",
                        "args": {
                            "source": "internal_kb",
                            "query_type": "competition_info",
                            "keywords": last_user[:80],
                        },
                    }
                )
            if asks_skills and not has_skill:
                augmented.append(
                    {
                        "id": None,
                        "name": "search_knowledge_repository",
                        "args": {
                            "source": "internal_kb",
                            "query_type": "skill_inference",
                            "keywords": last_user[:80],
                        },
                    }
                )
            if asks_advisor and not has_advisor:
                augmented.append(
                    {
                        "id": None,
                        "name": "execute_strategy_engine",
                        "args": {"action": "recommend_advisor", "context_data": {"note": "competition"}},
                    }
                )
            if asks_advisor and not has_team:
                augmented.append(
                    {
                        "id": None,
                        "name": "execute_strategy_engine",
                        "args": {"action": "analyze_team_model", "context_data": {"note": "competition"}},
                    }
                )
            if not has_profile:
                augmented.append(
                    {
                        "id": None,
                        "name": "get_user_comprehensive_profile",
                        "args": {"user_id": "default", "scope": "basic"},
                    }
                )
            return augmented
        if agent == "course":
            has_curriculum = any(
                call.get("name") == "query_institutional_database"
                and call.get("args", {}).get("category") == "curriculum"
                for call in augmented
            )
            has_search = any(
                call.get("name") == "search_knowledge_repository"
                and call.get("args", {}).get("query_type") == "tech_evolution"
                for call in augmented
            )
            mentions_course = any(
                key in last_user for key in ["课程", "选修", "必修", "学分", "培养方案", "毕业要求", "大纲"]
            )
            asks_path = any(key in last_user for key in ["怎么学", "难吗", "复习", "重点", "学习路径", "备考"])
            for call in augmented:
                if call.get("name") == "query_institutional_database":
                    args = call.setdefault("args", {})
                    if not args.get("category"):
                        args["category"] = "curriculum"
                    if not args.get("keywords"):
                        args["keywords"] = last_user[:60]
                if call.get("name") == "search_knowledge_repository":
                    args = call.setdefault("args", {})
                    if not args.get("source"):
                        args["source"] = "internal_kb"
                    if not args.get("query_type"):
                        args["query_type"] = "tech_evolution"
                    if not args.get("keywords"):
                        args["keywords"] = last_user[:80]
            if mentions_course and not has_curriculum:
                augmented.append(
                    {
                        "id": None,
                        "name": "query_institutional_database",
                        "args": {"category": "curriculum", "keywords": last_user[:60]},
                    }
                )
            if asks_path and not has_search:
                augmented.append(
                    {
                        "id": None,
                        "name": "search_knowledge_repository",
                        "args": {
                            "source": "internal_kb",
                            "query_type": "tech_evolution",
                            "keywords": last_user[:80],
                        },
                    }
                )
            if not has_profile:
                augmented.append(
                    {
                        "id": None,
                        "name": "get_user_comprehensive_profile",
                        "args": {"user_id": "default", "scope": "basic"},
                    }
                )
            return augmented
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


def _build_plan(tool_calls: list[dict[str, Any]], registry: ToolRegistry) -> dict[str, Any]:
    steps = []
    for call in tool_calls:
        name = call.get("name")
        contract = registry.get_contract(name) if name else None
        steps.append(
            {
                "tool": name,
                "args": call.get("args", {}),
                "expected_output": contract.get("output_schema") if contract else None,
                "auth_scope": contract.get("auth_scope") if contract else None,
                "rate_limit": contract.get("rate_limit") if contract else None,
            }
        )
    return {"steps": steps, "tool_count": len(steps)}


def identify_missing_slots(
    tool_calls: list[dict[str, Any]],
    registry: ToolRegistry,
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for call in tool_calls:
        name = call.get("name")
        schema = registry.get_schema(name) if name else None
        required = schema.get("required", []) if isinstance(schema, dict) else []
        if not required:
            continue
        missing_fields = []
        args = call.get("args", {})
        for field in required:
            value = args.get(field)
            if value is None or value == "":
                missing_fields.append(field)
        if missing_fields:
            missing.append({"tool": name, "missing": missing_fields})
    return missing


def build_missing_slots_question(missing_slots: list[dict[str, Any]]) -> str:
    lines = ["为了继续处理，我还需要补充以下信息："]
    for slot in missing_slots:
        tool = slot.get("tool") or "工具"
        fields = "、".join(slot.get("missing", []))
        lines.append(f"- {tool} 需要：{fields}")
    lines.append("请补充上述信息后再继续。")
    return "\n".join(lines)


def plan_with_tools(
    messages: list[dict[str, Any]],
    tools_payload: list[dict[str, Any]],
    model_name: str,
    api_key: str,
    base_url: str,
    registry: ToolRegistry,
    agent: str,
    user_id: int | None,
    conversation_id: int | None,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], bool, dict[str, Any]]:
    assistant_content = ""
    tool_calls: list[dict[str, Any]] = []
    raw_tool_calls: list[dict[str, Any]] = []
    used_json_fallback = False
    error: str | None = None
    if tools_payload:
        try:
            planning_content = ""
            assistant_content, tool_calls, raw_tool_calls = call_ai_model_with_tools(
                model_name,
                messages,
                api_key=api_key,
                base_url=base_url,
                tools=tools_payload,
            )
            planning_content = assistant_content
            if not tool_calls and assistant_content:
                tool_calls = _parse_json_tool_calls(assistant_content)
                used_json_fallback = bool(tool_calls)
            tool_calls = _augment_tool_calls(agent, messages, tool_calls)
            if assistant_content and _looks_like_tool_call_leak(assistant_content):
                assistant_content = ""
        except Exception as exc:
            logger.exception("Tool planning failed, falling back to no-tool flow")
            error = str(exc)
            planning_content = assistant_content

    plan = _build_plan(tool_calls, registry)
    write_agent_log(
        {
            "event": "orchestrator_plan",
            "agent": agent,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "tool_calls": raw_tool_calls,
            "assistant_content": planning_content if tools_payload else assistant_content,
            "json_fallback": used_json_fallback,
            "plan": plan,
            "error": error,
        }
    )

    return assistant_content, tool_calls, raw_tool_calls, used_json_fallback, plan


def execute_plan(
    tool_calls: list[dict[str, Any]],
    registry: ToolRegistry,
    db: Session,
    agent: str,
    user_id: int | None,
    conversation_id: int | None,
    allow_write: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tool_results = execute_tool_calls(
        tool_calls,
        registry,
        db,
        agent,
        user_id,
        conversation_id,
        allow_write=allow_write,
    )
    tool_names = [result.get("name") for result in tool_results if result.get("name")]
    error_count = sum(1 for result in tool_results if result.get("result", {}).get("status") == "error")
    redacted = any(result.get("result", {}).get("_meta", {}).get("redacted") for result in tool_results)
    truncated = any(result.get("result", {}).get("_meta", {}).get("truncated") for result in tool_results)
    summary = {
        "total": len(tool_results),
        "errors": error_count,
        "tools": sorted(set(tool_names)),
        "redacted": redacted,
        "truncated": truncated,
    }
    write_agent_log(
        {
            "event": "orchestrator_tool_results",
            "agent": agent,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "summary": summary,
        }
    )
    return tool_results, summary


def synthesize_with_tools(
    messages: list[dict[str, Any]],
    assistant_content: str,
    tool_calls: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    model_name: str,
    api_key: str,
    base_url: str,
    agent: str,
) -> str:
    if agent == "course" and not _tool_results_have_course_data(tool_results):
        fallback = _build_course_no_data_response(_extract_last_user_message(messages))
        write_agent_log(
            {
                "event": "course_empty_guard",
                "agent": agent,
                "note": "course response fallback used due to empty tool results",
            }
        )
        return fallback
    final_messages = _build_synthesis_messages(messages, assistant_content, tool_calls, tool_results)
    try:
        final_text = call_ai_model(
            model_name,
            final_messages,
            api_key=api_key,
            base_url=base_url,
            max_tokens=SYNTHESIS_MAX_TOKENS,
        )
        if _looks_like_tool_call_leak(final_text):
            final_messages.append({"role": "system", "content": RETRY_TOOL_LEAK_INSTRUCTION})
            final_text = call_ai_model(
                model_name,
                final_messages,
                api_key=api_key,
                base_url=base_url,
                max_tokens=SYNTHESIS_MAX_TOKENS,
            )
        if _looks_like_tool_call_leak(final_text):
            write_agent_log(
                {
                    "event": "tool_call_leak_guard",
                    "agent": agent,
                    "note": "synthesis response suppressed because it still contained tool-call format",
                }
            )
            return FALLBACK_MESSAGE
        return final_text
    except Exception:
        logger.exception("Synthesis failed, returning fallback response")
        return FALLBACK_MESSAGE


def stream_synthesize_with_tools(
    messages: list[dict[str, Any]],
    assistant_content: str,
    tool_calls: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    model_name: str,
    api_key: str,
    base_url: str,
    agent: str,
) -> Any:
    try:
        if agent == "course" and not _tool_results_have_course_data(tool_results):
            fallback = _build_course_no_data_response(_extract_last_user_message(messages))
            write_agent_log(
                {
                    "event": "course_empty_guard",
                    "agent": agent,
                    "note": "course response fallback used due to empty tool results",
                }
            )
            yield fallback
            return

        final_messages = _build_synthesis_messages(messages, assistant_content, tool_calls, tool_results)
        yield from _stream_with_tool_leak_guard(
            model_name,
            final_messages,
            api_key,
            base_url,
            {
                "event": "tool_call_leak_guard",
                "agent": agent,
                "note": "synthesis stream response suppressed because it still contained tool-call format",
            },
        )
    except Exception:
        logger.exception("Synthesis stream failed, returning fallback response")
        yield FALLBACK_MESSAGE


def stream_without_tools(
    model_name: str,
    messages: list[dict[str, Any]],
    api_key: str,
    base_url: str,
) -> Any:
    try:
        guarded_messages = messages + [{"role": "system", "content": DIRECT_NO_TOOL_INSTRUCTION}]
        yield from _stream_with_tool_leak_guard(
            model_name,
            guarded_messages,
            api_key,
            base_url,
            {
                "event": "tool_call_leak_guard",
                "note": "direct stream response suppressed because it still contained tool-call format",
            },
        )
    except Exception:
        logger.exception("Streaming failed, returning fallback response")
        yield FALLBACK_MESSAGE
