from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import REPORT_API_KEY, REPORT_BASE_URL, REPORT_MODEL, get_agent_model
from ..models import UserAcademicReport, UserCourseReport
from ..services.academics import list_course_objectives
from ..services.ai import call_ai_model

COURSE_REPORT_PROMPT_VERSION = "v1"
ACADEMIC_REPORT_PROMPT_VERSION = "v1"


def _resolve_report_model() -> str:
    return REPORT_MODEL or get_agent_model("course")


def _ensure_report_config() -> tuple[str, str, str]:
    model = _resolve_report_model()
    if not REPORT_API_KEY or not REPORT_BASE_URL or not model:
        raise RuntimeError("Report model is not configured")
    return REPORT_API_KEY, REPORT_BASE_URL, model


def _fetch_course_info(db: Session, offering_id: int) -> dict[str, Any]:
    sql = """
SELECT o.offering_id,
       o.teacher_name,
       c.course_code,
       c.course_name
  FROM dm.course_offerings o
  JOIN dm.courses c ON c.course_id = o.course_id
 WHERE o.offering_id = :offering_id
"""
    row = db.execute(text(sql), {"offering_id": offering_id}).mappings().first()
    if not row:
        return {}
    course_code = row.get("course_code")
    syllabus_row = None
    if course_code:
        syllabus_row = db.execute(
            text("SELECT syllabus_content FROM courses WHERE course_code = :course_code"),
            {"course_code": course_code},
        ).mappings().first()
    payload = dict(row)
    payload["syllabus_content"] = syllabus_row.get("syllabus_content") if syllabus_row else None
    return payload


def _format_objective_lines(objectives: list[dict[str, Any]]) -> str:
    lines = []
    for obj in objectives:
        percentile = obj.get("percentile")
        percentile_display = f"{percentile * 100:.1f}%" if isinstance(percentile, int | float) else "-"
        achievement = obj.get("achievement_score")
        achievement_display = (
            f"{achievement:.3f}" if isinstance(achievement, int | float) else "-"
        )
        lines.append(
            f"目标 {obj.get('objective_index') or obj.get('objective_id')}: {obj.get('description')} | "
            f"达成度 {achievement_display} | 班级分位 {percentile_display}"
        )
    return "\n".join(lines)


def generate_course_report(
    db: Session,
    user_id: int,
    student_no: str,
    offering_id: int,
    role: str = "student",
) -> UserCourseReport:
    api_key, base_url, model = _ensure_report_config()
    objectives = list_course_objectives(db, student_no, offering_id, role)
    if not objectives:
        raise RuntimeError("未找到课程目标数据")

    course_info = _fetch_course_info(db, offering_id)
    syllabus_content = (course_info.get("syllabus_content") or "").strip()
    syllabus_excerpt = syllabus_content[:1200] if syllabus_content else ""
    objective_lines = _format_objective_lines(objectives)

    prompt = (
        "你是高校教学评估顾问，请基于课程目标达成度数据生成个人学习报告。"
        "报告需分析学生优势与劣势，结合课程大纲内容给出改进建议。"
    )
    user_message = (
        f"课程信息：{course_info.get('course_code')}-{course_info.get('course_name')}，"
        f"任课教师 {course_info.get('teacher_name') or '未知'}。\n\n"
        f"课程目标与达成数据：\n{objective_lines}\n\n"
        f"课程大纲节选：\n{syllabus_excerpt or '无'}\n\n"
        "输出要求：150-300 字中文报告，包含优势、短板与改进建议。"
    )

    content = call_ai_model(
        model_name=model,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_message}],
        api_key=api_key,
        base_url=base_url,
        max_tokens=512,
        temperature=0.6,
    ).strip()

    source_snapshot = {
        "generated_at": datetime.utcnow().isoformat(),
        "objective_count": len(objectives),
        "course_code": course_info.get("course_code"),
    }

    existing = (
        db.query(UserCourseReport)
        .filter(UserCourseReport.user_id == user_id, UserCourseReport.offering_id == offering_id)
        .first()
    )
    if existing:
        existing.content = content
        existing.source_snapshot = source_snapshot
        existing.model = model
        existing.prompt_version = COURSE_REPORT_PROMPT_VERSION
        db.commit()
        db.refresh(existing)
        return existing

    report = UserCourseReport(
        user_id=user_id,
        offering_id=offering_id,
        content=content,
        source_snapshot=source_snapshot,
        model=model,
        prompt_version=COURSE_REPORT_PROMPT_VERSION,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def generate_academic_report(
    db: Session,
    user_id: int,
    student_no: str,
    requirements_snapshot: dict[str, Any],
    training_plan: list[dict[str, Any]],
) -> UserAcademicReport:
    api_key, base_url, model = _ensure_report_config()

    requirement_lines = []
    for req in requirements_snapshot.get("requirements", []):
        rate = req.get("achievement_rate")
        rate_display = f"{rate:.2f}" if isinstance(rate, int | float) else "-"
        status = "已达成" if req.get("achieved") else "待提升"
        requirement_lines.append(
            f"{req.get('index') or req.get('id')}: {req.get('description')} | 达成度 {rate_display} | {status}"
        )

    plan_lines = []
    for course in training_plan[:20]:
        plan_lines.append(
            f"{course.get('course_code')}-{course.get('course_name')}"
            f"({course.get('course_category') or '-'})"
        )

    prompt = (
        "你是高校学业规划导师，请根据学生毕业要求达成情况与培养方案，"
        "生成学业报告，分析优势与不足，并提出达成所有毕业要求的行动方案。"
    )
    user_message = (
        f"毕业要求达成情况：\n{chr(10).join(requirement_lines) or '无'}\n\n"
        f"培养方案课程（最多20条）：\n{chr(10).join(plan_lines) or '无'}\n\n"
        "要求：200-400 字中文报告，明确优势、短板与改进路径。"
    )

    content = call_ai_model(
        model_name=model,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_message}],
        api_key=api_key,
        base_url=base_url,
        max_tokens=700,
        temperature=0.6,
    ).strip()

    source_snapshot = {
        "generated_at": datetime.utcnow().isoformat(),
        "requirement_count": len(requirements_snapshot.get("requirements", [])),
    }

    existing = db.query(UserAcademicReport).filter(UserAcademicReport.user_id == user_id).first()
    if existing:
        existing.content = content
        existing.source_snapshot = source_snapshot
        existing.model = model
        existing.prompt_version = ACADEMIC_REPORT_PROMPT_VERSION
        db.commit()
        db.refresh(existing)
        return existing

    report = UserAcademicReport(
        user_id=user_id,
        content=content,
        source_snapshot=source_snapshot,
        model=model,
        prompt_version=ACADEMIC_REPORT_PROMPT_VERSION,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def build_training_plan(db: Session, program_id: int | None) -> list[dict[str, Any]]:
    if program_id is None:
        return []
    sql_version = """
SELECT program_version_id
  FROM dm.program_versions
 WHERE program_id = :program_id
   AND is_active = true
 ORDER BY updated_at DESC NULLS LAST
 LIMIT 1
"""
    version_row = db.execute(text(sql_version), {"program_id": program_id}).mappings().first()
    if not version_row:
        return []
    sql_courses = """
SELECT pvc.course_id,
       pvc.course_category,
       c.course_code,
       c.course_name
  FROM dm.program_version_courses pvc
  JOIN dm.courses c ON c.course_id = pvc.course_id
 WHERE pvc.program_version_id = :version_id
 ORDER BY pvc.display_order_primary NULLS LAST, pvc.display_order_secondary NULLS LAST, c.course_code
"""
    rows = db.execute(text(sql_courses), {"version_id": version_row["program_version_id"]}).mappings().all()
    return [dict(row) for row in rows]
