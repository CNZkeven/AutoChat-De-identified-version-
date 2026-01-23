from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import (
    SYSTEM_PROFILE_API_KEY,
    SYSTEM_PROFILE_BASE_URL,
    SYSTEM_PROFILE_MODEL,
    USER_PROFILE_API_KEY,
    USER_PROFILE_BASE_URL,
    USER_PROFILE_MODEL,
)
from ..db import SessionLocal
from ..models import User, UserPublicProfile, UserSystemProfile
from ..services.academics import get_student_academic_updates, list_student_courses
from ..services.ai import call_ai_model

SYSTEM_PROFILE_PROMPT_VERSION = "v1"
USER_PROFILE_PROMPT_VERSION = "v1"

logger = logging.getLogger(__name__)

@dataclass
class ProfileInputSnapshot:
    academic_updated_at: datetime | None
    memory_updated_at: datetime | None
    course_count: int
    courses: list[dict[str, Any]]
    memory_summaries: list[dict[str, Any]]


def _fetch_memory_summaries(db: Session, user_id: int) -> list[dict[str, Any]]:
    sql = """
SELECT agent, summary, updated_at
  FROM memory_summaries
 WHERE user_id = :user_id
 ORDER BY updated_at DESC NULLS LAST
"""
    rows = db.execute(text(sql), {"user_id": user_id}).mappings().all()
    return [dict(row) for row in rows]


def _build_profile_snapshot(
    db: Session, user: User, role: str = "student"
) -> ProfileInputSnapshot:
    student_no = user.username
    academic_meta = get_student_academic_updates(db, student_no, role)
    courses = list_student_courses(db, student_no, role)
    memory_summaries = _fetch_memory_summaries(db, user.id)
    return ProfileInputSnapshot(
        academic_updated_at=academic_meta.get("last_updated"),
        memory_updated_at=(memory_summaries[0]["updated_at"] if memory_summaries else None),
        course_count=len(courses),
        courses=courses,
        memory_summaries=memory_summaries,
    )


def _format_course_lines(courses: list[dict[str, Any]], limit: int = 12) -> str:
    lines = []
    for item in courses[:limit]:
        score = item.get("total_score")
        score_display = f"{score:.1f}" if isinstance(score, int | float) else (item.get("grade_text") or "-")
        percentile = item.get("percentile")
        percentile_display = f"{percentile * 100:.1f}%" if isinstance(percentile, int | float) else "-"
        lines.append(
            f"{item.get('course_code')}-{item.get('course_name')} | 任课: {item.get('teacher_name') or '-'} | 成绩: {score_display} | 分位: {percentile_display}"
        )
    return "\n".join(lines)


def _format_memory_lines(memory_summaries: list[dict[str, Any]], limit: int = 4) -> str:
    lines = []
    for item in memory_summaries[:limit]:
        summary = (item.get("summary") or "").strip()
        if not summary:
            continue
        lines.append(f"[{item.get('agent')}] {summary}")
    return "\n".join(lines)


def _generate_profile_content(
    *,
    user: User,
    snapshot: ProfileInputSnapshot,
    api_key: str,
    base_url: str,
    model: str,
    prompt_type: str,
) -> str:
    if not api_key or not base_url or not model:
        raise RuntimeError("Profile model is not configured")

    course_lines = _format_course_lines(snapshot.courses)
    memory_lines = _format_memory_lines(snapshot.memory_summaries)

    if prompt_type == "system":
        instruction = (
            "你是学生画像分析系统。请根据学生的学业数据与互动摘要，"
            "给出直白、明确、可操作的画像描述。避免空泛鼓励。"
        )
    else:
        instruction = (
            "你是高校辅导员，请基于学生学业表现与互动摘要，"
            "生成面向学生的积极画像，语言友好、鼓励、可理解。"
        )

    message = (
        f"学生信息：学号 {user.username}，姓名 {user.full_name or '未知'}，"
        f"专业 {user.major or '未知'}，年级 {user.grade or '未知'}，性别 {user.gender or '未知'}。\n\n"
        f"课程概览（最多12条）：\n{course_lines or '无'}\n\n"
        f"互动摘要（最多4条）：\n{memory_lines or '无'}\n\n"
        "要求：输出 200-400 字中文画像。"
    )

    content = call_ai_model(
        model_name=model,
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": message},
        ],
        api_key=api_key,
        base_url=base_url,
        max_tokens=512,
        temperature=0.5,
    )
    return content.strip()


def refresh_system_profile(user_id: int) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        snapshot = _build_profile_snapshot(db, user, role="admin")
        if not snapshot.course_count:
            return
        existing = db.query(UserSystemProfile).filter(UserSystemProfile.user_id == user_id).first()
        previous_snapshot = existing.source_snapshot if existing else {}
        academic_updated_at = snapshot.academic_updated_at
        memory_updated_at = snapshot.memory_updated_at
        if existing:
            if previous_snapshot.get("academic_updated_at") == str(academic_updated_at) and previous_snapshot.get(
                "memory_updated_at"
            ) == str(memory_updated_at):
                return
        try:
            content = _generate_profile_content(
                user=user,
                snapshot=snapshot,
                api_key=SYSTEM_PROFILE_API_KEY,
                base_url=SYSTEM_PROFILE_BASE_URL,
                model=SYSTEM_PROFILE_MODEL,
                prompt_type="system",
            )
        except Exception:
            logger.exception("Failed to generate system profile for user %s", user_id)
            return
        source_snapshot = {
            "academic_updated_at": str(academic_updated_at),
            "memory_updated_at": str(memory_updated_at),
            "course_count": snapshot.course_count,
        }
        if existing:
            existing.content = content
            existing.source_snapshot = source_snapshot
            existing.model = SYSTEM_PROFILE_MODEL
            existing.prompt_version = SYSTEM_PROFILE_PROMPT_VERSION
        else:
            db.add(
                UserSystemProfile(
                    user_id=user_id,
                    content=content,
                    source_snapshot=source_snapshot,
                    model=SYSTEM_PROFILE_MODEL,
                    prompt_version=SYSTEM_PROFILE_PROMPT_VERSION,
                )
            )
        db.commit()
    finally:
        db.close()


def generate_public_profile(db: Session, user: User) -> UserPublicProfile:
    snapshot = _build_profile_snapshot(db, user, role="admin")
    if not snapshot.course_count:
        raise RuntimeError("没有学业数据，无法生成画像")
    content = _generate_profile_content(
        user=user,
        snapshot=snapshot,
        api_key=USER_PROFILE_API_KEY,
        base_url=USER_PROFILE_BASE_URL,
        model=USER_PROFILE_MODEL,
        prompt_type="public",
    )
    source_snapshot = {
        "academic_updated_at": str(snapshot.academic_updated_at),
        "memory_updated_at": str(snapshot.memory_updated_at),
        "course_count": snapshot.course_count,
    }
    existing = db.query(UserPublicProfile).filter(UserPublicProfile.user_id == user.id).first()
    if existing:
        existing.content = content
        existing.source_snapshot = source_snapshot
        existing.model = USER_PROFILE_MODEL
        existing.prompt_version = USER_PROFILE_PROMPT_VERSION
        db.commit()
        db.refresh(existing)
        return existing
    profile = UserPublicProfile(
        user_id=user.id,
        content=content,
        source_snapshot=source_snapshot,
        model=USER_PROFILE_MODEL,
        prompt_version=USER_PROFILE_PROMPT_VERSION,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def fetch_system_profile(db: Session, user_id: int) -> UserSystemProfile | None:
    return db.query(UserSystemProfile).filter(UserSystemProfile.user_id == user_id).first()


def fetch_public_profile(db: Session, user_id: int) -> UserPublicProfile | None:
    return db.query(UserPublicProfile).filter(UserPublicProfile.user_id == user_id).first()
