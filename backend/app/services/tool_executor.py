import json
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from jose import jwt

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..config import (
    EXTERNAL_API_BASE_URL,
    EXTERNAL_API_TIMEOUT,
    EXTERNAL_JWT_AUDIENCE,
    EXTERNAL_JWT_EXPIRE_MINUTES,
    EXTERNAL_JWT_ISSUER,
    EXTERNAL_JWT_SECRET,
)
from ..models import Course, Knowledge, User, UserProfile
from .cache import (
    INSTITUTION_CACHE_TTL,
    KNOWLEDGE_CACHE_TTL,
    PROFILE_CACHE_TTL,
    cache_get,
    cache_set,
    make_cache_key,
)
from .tool_logging import write_agent_log
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_SIZE = 20
DEFAULT_MAX_TEXT = 800

EXTERNAL_SCOPE_SYLLABUS = "syllabus:read"
EXTERNAL_SCOPE_GRADES = "grades:read:own"
EXTERNAL_SCOPE_DISTRIBUTION = "grades:distribution:read"


def _build_external_token(student_no: str, scopes: list[str]) -> str:
    now = datetime.utcnow()
    payload = {
        "student_no": student_no,
        "scopes": scopes,
        "iss": EXTERNAL_JWT_ISSUER,
        "aud": EXTERNAL_JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=EXTERNAL_JWT_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, EXTERNAL_JWT_SECRET, algorithm="HS256")


def _external_get(
    path: str,
    student_no: str,
    scopes: list[str],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not EXTERNAL_API_BASE_URL:
        return {"status": "not_configured", "message": "external api base url missing"}
    try:
        token = _build_external_token(student_no, scopes)
    except Exception as exc:
        return {"status": "error", "message": "external jwt failed", "detail": str(exc)}
    url = f"{EXTERNAL_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        with httpx.Client(timeout=EXTERNAL_API_TIMEOUT) as client:
            response = client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
    except httpx.RequestError as exc:
        return {"status": "error", "message": "external request failed", "detail": str(exc)}
    try:
        payload = response.json()
    except Exception:
        payload = response.text
    if response.status_code >= 400:
        return {
            "status": "error",
            "http_status": response.status_code,
            "detail": payload,
        }
    return {"status": "ok", "data": payload}


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


def _validate_output(schema: dict[str, Any] | None, result: dict[str, Any]) -> list[str]:
    if not schema:
        return []
    if not isinstance(result, dict):
        return ["invalid_output_type"]
    required = schema.get("required", []) if isinstance(schema.get("required"), list) else []
    errors = []
    for key in required:
        if key not in result:
            errors.append(f"missing:{key}")
    return errors


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return json.dumps({"error": "serialization_failed"})


def _strip_instructional_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        lowered = line.strip().lower()
        if lowered.startswith(("system:", "assistant:", "user:", "tool:")):
            continue
        if "<tool_call>" in lowered or "```json" in lowered:
            continue
        lines.append(line)
    return "\n".join(lines)


def _sanitize_value(
    value: Any,
    safety_filter: set[str],
    meta: dict[str, Any],
) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in safety_filter:
                sanitized[key] = "***REDACTED***"
                meta["redacted"] = True
                continue
            sanitized[key] = _sanitize_value(item, safety_filter, meta)
        return sanitized
    if isinstance(value, list):
        if len(value) > DEFAULT_SAMPLE_SIZE:
            meta["truncated"] = True
            meta["total_items"] = len(value)
            value = value[:DEFAULT_SAMPLE_SIZE]
        return [_sanitize_value(item, safety_filter, meta) for item in value]
    if isinstance(value, str):
        if "instruction" in safety_filter:
            value = _strip_instructional_text(value)
        if len(value) > DEFAULT_MAX_TEXT:
            meta["truncated"] = True
            meta["truncated_fields"].append("text")
            return value[:DEFAULT_MAX_TEXT] + "..."
        return value
    return value


def _sanitize_result(result: dict[str, Any], safety_filter: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    meta = {"redacted": False, "truncated": False, "truncated_fields": []}
    safety_set = {str(item).lower() for item in safety_filter}
    sanitized = _sanitize_value(result, safety_set, meta)
    return sanitized if isinstance(sanitized, dict) else {"value": sanitized}, meta


def execute_tool_call(
    tool_name: str,
    args: dict[str, Any],
    db: Session,
) -> dict[str, Any]:
    if tool_name == "get_user_comprehensive_profile":
        user_id = args.get("user_id")
        if isinstance(user_id, str):
            if user_id.isdigit():
                user_id = int(user_id)
            else:
                user_id = None
        scope = args.get("scope")
        cache_key = make_cache_key(
            "tool:get_user_comprehensive_profile",
            {"user_id": user_id, "scope": scope},
        )
        cached = cache_get(cache_key)
        if cached is not None:
            cached["_cache"] = "hit"
            return cached
        profile = None
        if user_id is not None:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            result = {
                "status": "ok",
                "message": "user profile not found",
                "user_id": user_id,
                "scope": scope,
                "data": {},
                "note": "stub response",
            }
            cache_set(cache_key, result, PROFILE_CACHE_TTL)
            result["_cache"] = "miss"
            return result
        data = profile.data or {}
        scoped = data.get(scope) if isinstance(data, dict) else data
        result = {
            "status": "ok",
            "user_id": user_id,
            "scope": scope,
            "data": scoped if scoped is not None else data,
        }
        cache_set(cache_key, result, PROFILE_CACHE_TTL)
        result["_cache"] = "miss"
        return result

    if tool_name == "query_institutional_database":
        category = args.get("category")
        keywords = args.get("keywords", "")
        cache_key = make_cache_key(
            "tool:query_institutional_database",
            {"category": category, "keywords": keywords},
        )
        cached = cache_get(cache_key)
        if cached is not None:
            cached["_cache"] = "hit"
            return cached
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
            result = {
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
            cache_set(cache_key, result, INSTITUTION_CACHE_TTL)
            result["_cache"] = "miss"
            return result
        if category in {"competition_history", "research_strength"}:
            query = db.query(Knowledge)
            if keywords:
                like = f"%{keywords}%"
                query = query.filter(or_(Knowledge.title.ilike(like), Knowledge.content.ilike(like)))
            items = query.order_by(Knowledge.created_at.desc()).limit(10).all()
            result = {
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
            cache_set(cache_key, result, INSTITUTION_CACHE_TTL)
            result["_cache"] = "miss"
            return result
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
            cache_key = make_cache_key(
                "tool:search_knowledge_repository",
                {"source": source, "query_type": query_type, "keywords": keywords},
            )
            cached = cache_get(cache_key)
            if cached is not None:
                cached["_cache"] = "hit"
                return cached
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
            result = {
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
            cache_set(cache_key, result, KNOWLEDGE_CACHE_TTL)
            result["_cache"] = "miss"
            return result
        return {
            "status": "not_configured",
            "source": source,
            "query_type": query_type,
            "keywords": keywords,
            "message": "external repository not configured",
        }

    if tool_name == "fetch_external_student_academic_data":
        action = args.get("action")
        user_id = args.get("user_id")
        if not user_id:
            return {"status": "error", "message": "login_required"}
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"status": "error", "message": "user_not_found"}
        student_no = user.username
        if not student_no:
            return {"status": "error", "message": "student_no_missing"}

        def _coerce_int(value: Any) -> int | None:
            if value is None:
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
            return None

        def _to_bool(value: Any) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "y"}
            return False

        actions = {
            "list_course_offerings",
            "course_offering",
            "course_objectives",
            "course_grades",
            "course_achievements",
            "grade_distribution",
            "summary",
        }
        if action not in actions:
            return {"status": "error", "message": "unsupported action", "action": action}

        offering_id = _coerce_int(args.get("offering_id"))
        min_sample = _coerce_int(args.get("min_sample")) or 10
        include_grades = _to_bool(args.get("include_grades"))
        include_distribution = _to_bool(args.get("include_distribution"))
        max_offerings = _coerce_int(args.get("max_offerings")) or 8
        max_offerings = max(1, min(max_offerings, 20))

        if action == "list_course_offerings":
            result = _external_get(
                "/external/v1/students/me/course-offerings",
                student_no,
                [EXTERNAL_SCOPE_SYLLABUS],
            )
            result["action"] = action
            return result

        if action == "course_offering":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            result = _external_get(
                f"/external/v1/course-offerings/{offering_id}",
                student_no,
                [EXTERNAL_SCOPE_SYLLABUS],
            )
            result["action"] = action
            result["offering_id"] = offering_id
            return result

        if action == "course_objectives":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            result = _external_get(
                f"/external/v1/course-offerings/{offering_id}/objectives",
                student_no,
                [EXTERNAL_SCOPE_SYLLABUS],
            )
            result["action"] = action
            result["offering_id"] = offering_id
            return result

        if action == "course_grades":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            result = _external_get(
                f"/external/v1/students/me/course-offerings/{offering_id}/grades",
                student_no,
                [EXTERNAL_SCOPE_GRADES],
            )
            result["action"] = action
            result["offering_id"] = offering_id
            return result

        if action == "course_achievements":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            result = _external_get(
                f"/external/v1/students/me/course-offerings/{offering_id}/achievements",
                student_no,
                [EXTERNAL_SCOPE_GRADES],
            )
            result["action"] = action
            result["offering_id"] = offering_id
            return result

        if action == "grade_distribution":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            result = _external_get(
                f"/external/v1/course-offerings/{offering_id}/grades/distribution",
                student_no,
                [EXTERNAL_SCOPE_DISTRIBUTION],
                params={"minSample": min_sample},
            )
            result["action"] = action
            result["offering_id"] = offering_id
            result["min_sample"] = min_sample
            return result

        if action == "summary":
            list_result = _external_get(
                "/external/v1/students/me/course-offerings",
                student_no,
                [EXTERNAL_SCOPE_SYLLABUS],
            )
            if list_result.get("status") != "ok":
                list_result["action"] = action
                return list_result
            offerings = list_result.get("data")
            if not isinstance(offerings, list):
                return {
                    "status": "error",
                    "message": "unexpected offerings payload",
                    "action": action,
                }
            items = []
            for offering in offerings[:max_offerings]:
                current_id = offering.get("offeringId") if isinstance(offering, dict) else None
                entry = {"offering": offering}
                if current_id is None:
                    entry["error"] = "missing offeringId"
                    items.append(entry)
                    continue
                entry["objectives"] = _external_get(
                    f"/external/v1/course-offerings/{current_id}/objectives",
                    student_no,
                    [EXTERNAL_SCOPE_SYLLABUS],
                )
                entry["achievements"] = _external_get(
                    f"/external/v1/students/me/course-offerings/{current_id}/achievements",
                    student_no,
                    [EXTERNAL_SCOPE_GRADES],
                )
                if include_grades:
                    entry["grades"] = _external_get(
                        f"/external/v1/students/me/course-offerings/{current_id}/grades",
                        student_no,
                        [EXTERNAL_SCOPE_GRADES],
                    )
                if include_distribution:
                    entry["distribution"] = _external_get(
                        f"/external/v1/course-offerings/{current_id}/grades/distribution",
                        student_no,
                        [EXTERNAL_SCOPE_DISTRIBUTION],
                        params={"minSample": min_sample},
                    )
                items.append(entry)
            return {
                "status": "ok",
                "action": action,
                "student_no": student_no,
                "offerings_count": len(offerings),
                "returned": len(items),
                "items": items,
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
    allow_write: bool = False,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for call in tool_calls:
        name = call.get("name")
        args = call.get("args", {})
        contract = registry.get_contract(name) if name else None
        if name == "get_user_comprehensive_profile":
            if not args.get("user_id") or args.get("user_id") == "default":
                if user_id is not None:
                    args["user_id"] = user_id
            if not args.get("scope"):
                args["scope"] = "basic"
        if name == "fetch_external_student_academic_data":
            if user_id is not None:
                args["user_id"] = user_id
        if contract and contract.get("auth_scope") == "write" and not allow_write:
            result = {"status": "error", "message": "write_scope_blocked"}
            results.append({"id": call.get("id"), "name": name, "args": args, "result": result})
            continue
        schema = registry.get_schema(name) if name else None
        errors = _validate_args(schema, args) if name else ["missing_name"]
        if errors:
            result = {"status": "error", "errors": errors, "args": args}
        else:
            result = execute_tool_call(name, args, db)
        cache_status = result.pop("_cache", None)
        output_errors = _validate_output(contract.get("output_schema") if contract else None, result)
        if output_errors:
            result.setdefault("_meta", {})["output_errors"] = output_errors
        safety_filter = contract.get("safety_filter", []) if contract else []
        sanitized, meta = _sanitize_result(result, safety_filter)
        sanitized.setdefault("_meta", {})["cache"] = cache_status or "none"
        sanitized.setdefault("_meta", {}).update(meta)
        results.append(
            {
                "id": call.get("id"),
                "name": name,
                "args": args,
                "result": sanitized,
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
