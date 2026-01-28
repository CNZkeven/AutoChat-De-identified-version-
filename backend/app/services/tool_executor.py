import json
import logging
import re
from typing import Any

from sqlalchemy import String, bindparam, or_, text
from sqlalchemy.orm import Session

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

def _set_dm_session_context(db: Session, student_no: str | None, role: str | None) -> None:
    if student_no:
        db.execute(
            text("SELECT set_config('app.student_no', :student_no, true)"),
            {"student_no": student_no},
        )
    if role:
        db.execute(
            text("SELECT set_config('app.role', :role, true)"),
            {"role": role},
        )


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
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        text_value = str(value).strip()
        return text_value or None

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
        def _clean_text(value: Any) -> str | None:
            if value is None:
                return None
            text_value = str(value).strip()
            return text_value or None

        def _clean_text(value: Any) -> str | None:
            if value is None:
                return None
            text_value = str(value).strip()
            return text_value or None

        def _clean_text(value: Any) -> str | None:
            if value is None:
                return None
            text_value = str(value).strip()
            return text_value or None

        def _clean_text(value: Any) -> str | None:
            if value is None:
                return None
            text_value = str(value).strip()
            return text_value or None

        def _clean_text(value: Any) -> str | None:
            if value is None:
                return None
            text_value = str(value).strip()
            return text_value or None

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

        category = _clean_text(args.get("category"))
        keywords = _clean_text(args.get("keywords"))
        program_id = _coerce_int(args.get("program_id"))
        program_version_id = _coerce_int(args.get("program_version_id"))
        program_name = _clean_text(args.get("program_name"))
        program_version_name = _clean_text(args.get("program_version_name"))
        course_nature = _clean_text(args.get("course_nature"))
        course_category = _clean_text(args.get("course_category"))
        planned_semester = _clean_text(args.get("planned_semester"))
        course_code = _clean_text(args.get("course_code"))
        course_name = _clean_text(args.get("course_name"))
        limit = _coerce_int(args.get("limit")) or 20
        limit = max(1, min(limit, 50))
        include_syllabus = _to_bool(args.get("include_syllabus"))
        user_id = args.get("user_id")

        if category == "curriculum":
            student_no = None
            if user_id is not None:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.username:
                    student_no = user.username
            if student_no:
                _set_dm_session_context(db, student_no, "student")
                if program_id is None:
                    program_row = db.execute(
                        text("SELECT program_id FROM dm.students WHERE student_no = :student_no LIMIT 1"),
                        {"student_no": student_no},
                    ).first()
                    program_id = program_row[0] if program_row else None

            if keywords and not course_nature:
                if "选修" in keywords:
                    course_nature = "选修"
                elif "必修" in keywords:
                    course_nature = "必修"

            if keywords and not course_category:
                if "学科基础" in keywords:
                    course_category = "学科基础课程"
                elif "通识" in keywords:
                    course_category = "通识教育课程"
                elif "专业" in keywords and ("课程" in keywords or "专业课" in keywords or "专业选修" in keywords):
                    course_category = "专业课程"

            if not program_name and keywords:
                program_row = db.execute(
                    text(
                        """
SELECT program_id, name
  FROM dm.programs
 WHERE :keywords ILIKE '%' || name || '%'
 ORDER BY length(name) DESC
 LIMIT 1
"""
                    ),
                    {"keywords": keywords},
                ).first()
                if program_row:
                    program_id = program_row[0]
                    program_name = program_row[1]

            if not program_version_name and keywords:
                match = re.search(r"(20\\d{2})\\s*版", keywords)
                if match:
                    program_version_name = f"{match.group(1)}版"

            if keywords:
                trimmed = keywords.replace("？", "").replace("?", "").strip()
                if any(token in trimmed for token in ("有哪些", "有什么", "哪些课程", "哪些课")):
                    keywords = None
                elif (course_nature or course_category or program_name or program_id or program_version_id) and any(
                    token in trimmed for token in ("专业", "选修", "必修", "课程", "学科基础", "通识")
                ):
                    keywords = None
                else:
                    keywords = trimmed or None

            if program_id is None and program_name:
                program_row = db.execute(
                    text(
                        """
SELECT program_id
  FROM dm.programs
 WHERE name ILIKE :program_name
 ORDER BY CASE WHEN name = :program_name_exact THEN 0 ELSE 1 END, name ASC
 LIMIT 1
"""
                    ),
                    {"program_name": f"%{program_name}%", "program_name_exact": program_name},
                ).first()
                program_id = program_row[0] if program_row else None

            if program_version_id is None and program_id:
                version_sql = """
SELECT program_version_id
  FROM dm.program_versions
 WHERE program_id = :program_id
   AND (:version_name IS NULL OR version_name ILIKE :version_name)
 ORDER BY is_active DESC, updated_at DESC NULLS LAST
 LIMIT 1
"""
                stmt = text(version_sql).bindparams(bindparam("version_name", type_=String()))
                version_row = db.execute(
                    stmt,
                    {"program_id": program_id, "version_name": program_version_name},
                ).first()
                program_version_id = version_row[0] if version_row else None

            cache_payload = {
                "category": category,
                "keywords": keywords,
                "program_id": program_id,
                "program_version_id": program_version_id,
                "program_name": program_name,
                "program_version_name": program_version_name,
                "course_nature": course_nature,
                "course_category": course_category,
                "planned_semester": planned_semester,
                "course_code": course_code,
                "course_name": course_name,
                "limit": limit,
                "include_syllabus": include_syllabus,
            }
            if user_id is not None:
                cache_payload["user_id"] = user_id
            cache_key = make_cache_key("tool:query_institutional_database", cache_payload)
            cached = cache_get(cache_key)
            if cached is not None:
                cached["_cache"] = "hit"
                return cached

            if program_version_id:
                keyword_like = f"%{keywords}%" if keywords else None
                course_code_like = f"%{course_code}%" if course_code else None
                course_name_like = f"%{course_name}%" if course_name else None
                sql = """
SELECT pvc.course_id,
       c.course_code,
       c.course_name,
       c.credits,
       pvc.course_category,
       pvc.course_nature,
       pvc.planned_semester,
       pvc.plan_remarks,
       pvc.display_order_label
  FROM dm.program_version_courses pvc
  JOIN dm.courses c ON c.course_id = pvc.course_id
 WHERE pvc.program_version_id = :program_version_id
   AND (:course_nature IS NULL OR pvc.course_nature = :course_nature)
   AND (:course_category IS NULL OR pvc.course_category = :course_category)
   AND (:planned_semester IS NULL OR pvc.planned_semester = :planned_semester)
   AND (:course_code IS NULL OR c.course_code ILIKE :course_code)
   AND (:course_name IS NULL OR c.course_name ILIKE :course_name)
   AND (:kw IS NULL OR c.course_name ILIKE :kw OR c.course_code ILIKE :kw)
 ORDER BY pvc.display_order_primary NULLS LAST,
          pvc.display_order_secondary NULLS LAST,
          c.course_code ASC
 LIMIT :limit
"""
                stmt = text(sql).bindparams(
                    bindparam("kw", type_=String()),
                    bindparam("course_code", type_=String()),
                    bindparam("course_name", type_=String()),
                    bindparam("course_nature", type_=String()),
                    bindparam("course_category", type_=String()),
                    bindparam("planned_semester", type_=String()),
                )
                rows = db.execute(
                    stmt,
                    {
                        "program_version_id": program_version_id,
                        "course_nature": course_nature,
                        "course_category": course_category,
                        "planned_semester": planned_semester,
                        "course_code": course_code_like,
                        "course_name": course_name_like,
                        "kw": keyword_like,
                        "limit": limit,
                    },
                ).mappings()
                results = []
                for row in rows:
                    item = dict(row)
                    if include_syllabus:
                        syllabus_row = db.execute(
                            text(
                                """
SELECT syllabus_version_id,
       version_name,
       basic_info,
       process_requirements
  FROM dm.syllabus_versions
 WHERE course_id = :course_id
 ORDER BY is_default DESC, updated_at DESC NULLS LAST
 LIMIT 1
"""
                            ),
                            {"course_id": row["course_id"]},
                        ).mappings().first()
                        if syllabus_row:
                            item["syllabus"] = dict(syllabus_row)
                    results.append(item)
                result = {
                    "status": "ok",
                    "category": category,
                    "keywords": keywords,
                    "student_no": student_no,
                    "program_id": program_id,
                    "program_name": program_name,
                    "program_version_id": program_version_id,
                    "program_version_name": program_version_name,
                    "filters": {
                        "course_nature": course_nature,
                        "course_category": course_category,
                        "planned_semester": planned_semester,
                        "course_code": course_code,
                        "course_name": course_name,
                        "limit": limit,
                    },
                    "results": results,
                    "source": "dm",
                }
                cache_set(cache_key, result, INSTITUTION_CACHE_TTL)
                result["_cache"] = "miss"
                return result

            query = db.query(Course)
            if keywords or course_code or course_name:
                like = f"%{keywords}%" if keywords else None
                course_code_like = f"%{course_code}%" if course_code else None
                course_name_like = f"%{course_name}%" if course_name else None
                filters = []
                if like:
                    filters.extend(
                        [
                            Course.course_name.ilike(like),
                            Course.course_code.ilike(like),
                            Course.major.ilike(like),
                        ]
                    )
                if course_code_like:
                    filters.append(Course.course_code.ilike(course_code_like))
                if course_name_like:
                    filters.append(Course.course_name.ilike(course_name_like))
                if filters:
                    query = query.filter(or_(*filters))
            courses = query.order_by(Course.course_code.asc()).limit(min(limit, 20)).all()
            result = {
                "status": "ok",
                "category": category,
                "keywords": keywords,
                "filters": {
                    "course_code": course_code,
                    "course_name": course_name,
                    "limit": limit,
                },
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
                "source": "local",
            }
            cache_set(cache_key, result, INSTITUTION_CACHE_TTL)
            result["_cache"] = "miss"
            return result

        if category in {"competition_history", "research_strength"}:
            cache_payload = {"category": category, "keywords": keywords}
            cache_key = make_cache_key("tool:query_institutional_database", cache_payload)
            cached = cache_get(cache_key)
            if cached is not None:
                cached["_cache"] = "hit"
                return cached
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

    if tool_name == "fetch_dm_student_academic_data":
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
            "list_scores",
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
        max_offerings = _coerce_int(args.get("max_offerings"))
        summary_limit = max_offerings or 8
        summary_limit = max(1, min(summary_limit, 20))
        term = _clean_text(args.get("term"))
        course_keyword = _clean_text(args.get("course_keyword"))
        course_code = _clean_text(args.get("course_code"))
        course_name = _clean_text(args.get("course_name"))

        _set_dm_session_context(db, student_no, "student")

        def _fetch_offering_list(limit: int | None = None) -> list[dict[str, Any]]:
            sql = """
SELECT e.offering_id,
       o.section_name,
       o.class_number,
       o.teacher_name,
       t.term_name,
       c.course_code,
       c.course_name
  FROM dm.enrollments e
  JOIN dm.course_offerings o ON o.offering_id = e.offering_id
  JOIN dm.courses c ON c.course_id = o.course_id
  LEFT JOIN dm.academic_terms t ON t.term_id = o.term_id
 WHERE e.student_no = :student_no
   AND (:term IS NULL OR t.term_name = :term)
   AND (:course_code IS NULL OR c.course_code ILIKE :course_code)
   AND (:course_name IS NULL OR c.course_name ILIKE :course_name)
   AND (
       :course_keyword IS NULL
       OR c.course_name ILIKE :course_keyword
       OR c.course_code ILIKE :course_keyword
   )
   AND COALESCE(o.is_in_class_experiment, false) = false
 ORDER BY t.start_year DESC NULLS LAST,
          t.term_index DESC NULLS LAST,
          o.class_number ASC NULLS LAST,
          c.course_code ASC
"""
            params = {
                "student_no": student_no,
                "term": term,
                "course_keyword": f"%{course_keyword}%" if course_keyword else None,
                "course_code": f"%{course_code}%" if course_code else None,
                "course_name": f"%{course_name}%" if course_name else None,
            }
            if limit:
                sql += " LIMIT :limit"
                params["limit"] = limit
            stmt = text(sql).bindparams(
                bindparam("term", type_=String()),
                bindparam("course_keyword", type_=String()),
                bindparam("course_code", type_=String()),
                bindparam("course_name", type_=String()),
            )
            rows = db.execute(stmt, params).mappings()
            return [dict(row) for row in rows]

        def _fetch_offering(offering: int) -> dict[str, Any] | None:
            sql = """
SELECT o.offering_id,
       o.section_name,
       o.class_number,
       o.teacher_name,
       t.term_name,
       c.course_code,
       c.course_name,
       c.credits
  FROM dm.course_offerings o
  JOIN dm.courses c ON c.course_id = o.course_id
  LEFT JOIN dm.academic_terms t ON t.term_id = o.term_id
 WHERE o.offering_id = :offering_id
"""
            row = db.execute(text(sql), {"offering_id": offering}).mappings().first()
            return dict(row) if row else None

        def _fetch_objectives(offering: int) -> list[dict[str, Any]]:
            sql = """
SELECT objective_id,
       objective_index,
       description,
       objective_type
  FROM dm.course_objectives
 WHERE offering_id = :offering_id
 ORDER BY objective_id ASC
"""
            rows = db.execute(text(sql), {"offering_id": offering}).mappings()
            return [dict(row) for row in rows]

        def _fetch_grade(offering: int) -> dict[str, Any] | None:
            sql = """
SELECT offering_id,
       total_score,
       grade_text,
       score_source
  FROM dm.student_scores
 WHERE offering_id = :offering_id
   AND student_no = :student_no
"""
            row = db.execute(
                text(sql), {"offering_id": offering, "student_no": student_no}
            ).mappings().first()
            return dict(row) if row else None

        def _fetch_scores(limit: int | None = None) -> list[dict[str, Any]]:
            sql = """
SELECT s.offering_id,
       o.class_number,
       s.total_score,
       s.grade_text,
       s.score_source,
       t.term_name,
       c.course_code,
       c.course_name
  FROM dm.student_scores s
  JOIN dm.course_offerings o ON o.offering_id = s.offering_id
  JOIN dm.courses c ON c.course_id = o.course_id
  LEFT JOIN dm.academic_terms t ON t.term_id = o.term_id
 WHERE s.student_no = :student_no
   AND (:term IS NULL OR t.term_name = :term)
   AND (:course_code IS NULL OR c.course_code ILIKE :course_code)
   AND (:course_name IS NULL OR c.course_name ILIKE :course_name)
   AND (
       :course_keyword IS NULL
       OR c.course_name ILIKE :course_keyword
       OR c.course_code ILIKE :course_keyword
   )
   AND COALESCE(o.is_in_class_experiment, false) = false
 ORDER BY t.start_year DESC NULLS LAST,
          t.term_index DESC NULLS LAST,
          o.class_number ASC NULLS LAST,
          c.course_code ASC
"""
            params = {
                "student_no": student_no,
                "term": term,
                "course_keyword": f"%{course_keyword}%" if course_keyword else None,
                "course_code": f"%{course_code}%" if course_code else None,
                "course_name": f"%{course_name}%" if course_name else None,
            }
            if limit:
                sql += " LIMIT :limit"
                params["limit"] = limit
            stmt = text(sql).bindparams(
                bindparam("term", type_=String()),
                bindparam("course_keyword", type_=String()),
                bindparam("course_code", type_=String()),
                bindparam("course_name", type_=String()),
            )
            rows = db.execute(stmt, params).mappings()
            return [dict(row) for row in rows]

        def _fetch_achievements(offering: int) -> list[dict[str, Any]]:
            sql = """
SELECT objective_id,
       achievement_score,
       total_score,
       max_score
  FROM dm.student_objective_achievements
 WHERE offering_id = :offering_id
   AND student_no = :student_no
 ORDER BY objective_id ASC
"""
            rows = db.execute(
                text(sql), {"offering_id": offering, "student_no": student_no}
            ).mappings()
            return [dict(row) for row in rows]

        def _fetch_distribution(offering: int) -> dict[str, Any] | None:
            sql = """
SELECT offering_id,
       n_students,
       avg_score,
       min_score,
       max_score,
       dist_json
  FROM dm.section_grade_summary
 WHERE offering_id = :offering_id
"""
            row = db.execute(text(sql), {"offering_id": offering}).mappings().first()
            if not row:
                return None
            payload = dict(row)
            if payload.get("n_students") is not None and payload["n_students"] < min_sample:
                payload["note"] = "insufficient_sample"
            return payload

        def _is_in_class_experiment(offering: int) -> bool:
            row = db.execute(
                text(
                    """
SELECT COALESCE(is_in_class_experiment, false) AS flag
  FROM dm.course_offerings
 WHERE offering_id = :offering_id
"""
                ),
                {"offering_id": offering},
            ).mappings().first()
            return bool(row["flag"]) if row else False

        def _guard_offering(offering: int) -> dict[str, Any] | None:
            if _is_in_class_experiment(offering):
                return {"status": "error", "message": "in_class_experiment_filtered", "offering_id": offering}
            return None

        if action == "list_course_offerings":
            return {
                "status": "ok",
                "action": action,
                "student_no": student_no,
                "filters": {
                    "term": term,
                    "course_keyword": course_keyword,
                    "course_code": course_code,
                    "course_name": course_name,
                },
                "items": _fetch_offering_list(max_offerings),
            }

        if action == "list_scores":
            return {
                "status": "ok",
                "action": action,
                "student_no": student_no,
                "filters": {
                    "term": term,
                    "course_keyword": course_keyword,
                    "course_code": course_code,
                    "course_name": course_name,
                },
                "items": _fetch_scores(max_offerings),
            }

        if action == "course_offering":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            blocked = _guard_offering(offering_id)
            if blocked:
                return blocked
            return {
                "status": "ok",
                "action": action,
                "offering_id": offering_id,
                "data": _fetch_offering(offering_id),
            }

        if action == "course_objectives":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            blocked = _guard_offering(offering_id)
            if blocked:
                return blocked
            return {
                "status": "ok",
                "action": action,
                "offering_id": offering_id,
                "data": _fetch_objectives(offering_id),
            }

        if action == "course_grades":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            blocked = _guard_offering(offering_id)
            if blocked:
                return blocked
            return {
                "status": "ok",
                "action": action,
                "offering_id": offering_id,
                "data": _fetch_grade(offering_id),
            }

        if action == "course_achievements":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            blocked = _guard_offering(offering_id)
            if blocked:
                return blocked
            return {
                "status": "ok",
                "action": action,
                "offering_id": offering_id,
                "data": _fetch_achievements(offering_id),
            }

        if action == "grade_distribution":
            if offering_id is None:
                return {"status": "error", "message": "missing offering_id"}
            blocked = _guard_offering(offering_id)
            if blocked:
                return blocked
            return {
                "status": "ok",
                "action": action,
                "offering_id": offering_id,
                "min_sample": min_sample,
                "data": _fetch_distribution(offering_id),
            }

        if action == "summary":
            offerings = _fetch_offering_list(summary_limit)
            items: list[dict[str, Any]] = []
            for offering in offerings:
                current_id = offering.get("offering_id")
                entry = {"offering": offering}
                if not current_id:
                    entry["error"] = "missing offering_id"
                    items.append(entry)
                    continue
                entry["objectives"] = _fetch_objectives(current_id)
                entry["achievements"] = _fetch_achievements(current_id)
                if include_grades:
                    entry["grades"] = _fetch_grade(current_id)
                if include_distribution:
                    entry["distribution"] = _fetch_distribution(current_id)
                items.append(entry)
            return {
                "status": "ok",
                "action": action,
                "student_no": student_no,
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
        if name in {"fetch_dm_student_academic_data", "query_institutional_database"}:
            if user_id is not None:
                args.setdefault("user_id", user_id)
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
