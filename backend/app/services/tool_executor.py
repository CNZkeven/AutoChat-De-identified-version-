import json
import logging
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Course, Knowledge, UserProfile
from .tool_logging import write_agent_log
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def _validate_args(schema: dict[str, Any] | None, args: dict[str, Any]) -> list[str]:
    if not schema:
        return ["missing_schema"]
    required = schema.get("required", []) if isinstance(schema.get("required"), list) else []
    errors = []
    for key in required:
        value = args.get(key)
        if key not in args or value is None or value == "":
            errors.append(f"missing:{key}")
    return errors


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return json.dumps({"error": "serialization_failed"})


def execute_tool_call(
    tool_name: str,
    args: dict[str, Any],
    db: Session,
) -> dict[str, Any]:
    if tool_name == "get_user_comprehensive_profile":
        user_id = args.get("user_id")
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        scope = args.get("scope")
        profile = None
        if user_id is not None:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return {
                "status": "ok",
                "message": "user profile not found",
                "user_id": user_id,
                "scope": scope,
                "data": {},
                "note": "stub response",
            }
        data = profile.data or {}
        scoped = data.get(scope) if isinstance(data, dict) else data
        return {
            "status": "ok",
            "user_id": user_id,
            "scope": scope,
            "data": scoped if scoped is not None else data,
        }

    if tool_name == "query_institutional_database":
        category = args.get("category")
        keywords = args.get("keywords", "")
        if category == "curriculum":
            query = db.query(Course)
            if keywords:
                like = f"%{keywords}%"
                query = query.filter(
                    or_(
                        Course.course_name.ilike(like),
                        Course.course_code.ilike(like),
                        Course.major.ilike(like),
                    )
                )
            courses = query.order_by(Course.course_code.asc()).limit(10).all()
            return {
                "status": "ok",
                "category": category,
                "keywords": keywords,
                "results": [
                    {
                        "course_code": c.course_code,
                        "course_name": c.course_name,
                        "credits": c.credits,
                        "course_type": c.course_type,
                        "course_nature": c.course_nature,
                        "major": c.major,
                        "offering_semester": c.offering_semester,
                        "syllabus_status": c.syllabus_status,
                    }
                    for c in courses
                ],
            }
        if category in {"competition_history", "research_strength"}:
            query = db.query(Knowledge)
            if keywords:
                like = f"%{keywords}%"
                query = query.filter(or_(Knowledge.title.ilike(like), Knowledge.content.ilike(like)))
            items = query.order_by(Knowledge.created_at.desc()).limit(10).all()
            return {
                "status": "ok",
                "category": category,
                "keywords": keywords,
                "results": [
                    {
                        "title": item.title,
                        "category": item.category,
                        "source": item.source,
                    }
                    for item in items
                ],
                "note": "knowledge table used as institutional data placeholder",
            }
        return {
            "status": "error",
            "message": "unsupported category",
            "category": category,
        }

    if tool_name == "search_knowledge_repository":
        source = args.get("source")
        query_type = args.get("query_type")
        keywords = args.get("keywords", "")
        if source == "internal_kb":
            query = db.query(Knowledge).filter(Knowledge.source == "internal_kb")
            if query_type:
                query = query.filter(Knowledge.category == query_type)
            if keywords:
                like = f"%{keywords}%"
                query = query.filter(or_(Knowledge.title.ilike(like), Knowledge.content.ilike(like)))
            items = query.order_by(Knowledge.created_at.desc()).limit(10).all()
            fallback_used = False
            if not items and query_type:
                fallback_used = True
                query = db.query(Knowledge).filter(
                    Knowledge.source == "internal_kb", Knowledge.category == query_type
                )
                items = query.order_by(Knowledge.created_at.desc()).limit(10).all()
            return {
                "status": "ok",
                "source": source,
                "query_type": query_type,
                "keywords": keywords,
                "results": [
                    {
                        "title": item.title,
                        "category": item.category,
                        "source": item.source,
                        "content": item.content,
                    }
                    for item in items
                ],
                "fallback_used": fallback_used,
            }
        return {
            "status": "not_configured",
            "source": source,
            "query_type": query_type,
            "keywords": keywords,
            "message": "external repository not configured",
        }

    if tool_name == "execute_strategy_engine":
        action = args.get("action")
        context_data = args.get("context_data", {})
        if action == "check_error_book":
            return {
                "status": "ok",
                "action": action,
                "frequent_errors": [],
                "note": "stub response",
            }
        if action == "generate_plan":
            return {
                "status": "ok",
                "action": action,
                "plan": [],
                "note": "stub response",
            }
        if action in {"recommend_advisor", "analyze_team_model", "log_milestone"}:
            return {
                "status": "ok",
                "action": action,
                "result": [],
                "context_data": context_data,
                "note": "stub response",
            }
        return {
            "status": "error",
            "action": action,
            "message": "unsupported action",
        }

    return {
        "status": "error",
        "message": "unknown tool",
        "tool": tool_name,
    }


def execute_tool_calls(
    tool_calls: list[dict[str, Any]],
    registry: ToolRegistry,
    db: Session,
    agent: str,
    user_id: int | None,
    conversation_id: int | None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for call in tool_calls:
        name = call.get("name")
        args = call.get("args", {})
        if name == "get_user_comprehensive_profile":
            if not args.get("user_id") or args.get("user_id") == "default":
                if user_id is not None:
                    args["user_id"] = user_id
            if not args.get("scope"):
                args["scope"] = "basic"
        schema = registry.get_schema(name) if name else None
        errors = _validate_args(schema, args) if name else ["missing_name"]
        if errors:
            result = {"status": "error", "errors": errors, "args": args}
        else:
            result = execute_tool_call(name, args, db)
        results.append(
            {
                "id": call.get("id"),
                "name": name,
                "args": args,
                "result": result,
            }
        )

    write_agent_log(
        {
            "event": "tool_calls",
            "agent": agent,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "tool_calls": results,
        }
    )

    return results
