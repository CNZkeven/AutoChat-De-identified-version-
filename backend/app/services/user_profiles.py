from __future__ import annotations

import logging
from dataclasses import dataclass, field
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
from ..models import Conversation, Message, User, UserPublicProfile, UserSystemProfile
from ..services.academics import get_student_academic_updates, list_student_courses
from ..services.ai import call_ai_model

SYSTEM_PROFILE_PROMPT_VERSION = "v1"
USER_PROFILE_PROMPT_VERSION = "v1"

logger = logging.getLogger(__name__)

PUBLIC_PROFILE_DIALOGUE_ONLY_PREFIX = "未连接学生数据库，仅根据对话记录生成"
PUBLIC_PROFILE_NO_DATA_MESSAGE = "无对话记录和学生数据库，无法生成"

@dataclass
class ProfileInputSnapshot:
    academic_updated_at: datetime | None
    memory_updated_at: datetime | None
    course_count: int
    courses: list[dict[str, Any]]
    memory_summaries: list[dict[str, Any]]
    conversation_history: list[dict[str, Any]] = field(default_factory=list)


def _fetch_memory_summaries(db: Session, user_id: int) -> list[dict[str, Any]]:
    sql = """
SELECT agent, summary, updated_at
  FROM memory_summaries
 WHERE user_id = :user_id
 ORDER BY updated_at DESC NULLS LAST
"""
    rows = db.execute(text(sql), {"user_id": user_id}).mappings().all()
    return [dict(row) for row in rows]


def _fetch_conversation_history(db: Session, user_id: int, limit: int = 40) -> list[dict[str, Any]]:
    rows = (
        db.query(Conversation.agent, Message.role, Message.content, Message.created_at)
        .join(Message, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "agent": agent,
            "role": role,
            "content": content,
            "created_at": created_at,
        }
        for agent, role, content, created_at in reversed(rows)
    ]


def _build_profile_snapshot(
    db: Session, user: User, role: str = "student"
) -> ProfileInputSnapshot:
    student_no = user.username
    academic_meta = get_student_academic_updates(db, student_no, role)
    courses = list_student_courses(db, student_no, role)
    memory_summaries = _fetch_memory_summaries(db, user.id)
    conversation_history = _fetch_conversation_history(db, user.id)
    return ProfileInputSnapshot(
        academic_updated_at=academic_meta.get("last_updated"),
        memory_updated_at=(
            memory_summaries[0]["updated_at"]
            if memory_summaries
            else (conversation_history[-1]["created_at"] if conversation_history else None)
        ),
        course_count=len(courses),
        courses=courses,
        memory_summaries=memory_summaries,
        conversation_history=conversation_history,
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


def _format_conversation_history_lines(conversation_history: list[dict[str, Any]], limit: int = 20) -> str:
    lines = []
    for item in conversation_history[-limit:]:
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if len(content) > 300:
            content = content[:300] + "..."
        role = "用户" if item.get("role") == "user" else "AI"
        lines.append(f"[{item.get('agent')}] {role}: {content}")
    return "\n".join(lines)


def _format_dialogue_context(snapshot: ProfileInputSnapshot) -> str:
    sections = []
    memory_lines = _format_memory_lines(snapshot.memory_summaries)
    conversation_lines = _format_conversation_history_lines(snapshot.conversation_history)
    if memory_lines:
        sections.append(f"互动摘要：\n{memory_lines}")
    if conversation_lines:
        sections.append(f"历史对话：\n{conversation_lines}")
    return "\n\n".join(sections)


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
    dialogue_context = _format_dialogue_context(snapshot)

    if prompt_type == "system":
        instruction = (
            "你是学生画像分析系统。请根据学生的学业数据与互动摘要，"
            "给出直白、明确、可操作的画像描述。避免空泛鼓励。"
        )
    elif snapshot.course_count:
        instruction = (
            "你是高校辅导员，请基于学生学业表现与互动摘要，"
            "生成面向学生的积极画像，语言友好、鼓励、可理解。"
        )
    else:
        instruction = (
            "你是高校辅导员，请仅基于学生历史对话记录与互动摘要，"
            "生成面向学生的积极画像，语言友好、鼓励、可理解。"
        )

    message = (
        f"学生信息：学号 {user.username}，姓名 {user.full_name or '未知'}，"
        f"专业 {user.major or '未知'}，年级 {user.grade or '未知'}，性别 {user.gender or '未知'}。\n\n"
        f"课程概览（最多12条）：\n{course_lines or '无'}\n\n"
        f"互动摘要与历史对话：\n{dialogue_context or '无'}\n\n"
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


def _public_profile_source_snapshot(snapshot: ProfileInputSnapshot, basis: str) -> dict[str, str | int]:
    return {
        "academic_updated_at": str(snapshot.academic_updated_at),
        "memory_updated_at": str(snapshot.memory_updated_at),
        "course_count": snapshot.course_count,
        "conversation_count": len(snapshot.conversation_history),
        "basis": basis,
    }


def _save_public_profile(
    db: Session,
    user_id: int,
    content: str,
    source_snapshot: dict[str, str | int],
) -> UserPublicProfile:
    existing = db.query(UserPublicProfile).filter(UserPublicProfile.user_id == user_id).first()
    if existing:
        existing.content = content
        existing.source_snapshot = source_snapshot
        existing.model = USER_PROFILE_MODEL
        existing.prompt_version = USER_PROFILE_PROMPT_VERSION
        db.commit()
        db.refresh(existing)
        return existing
    profile = UserPublicProfile(
        user_id=user_id,
        content=content,
        source_snapshot=source_snapshot,
        model=USER_PROFILE_MODEL,
        prompt_version=USER_PROFILE_PROMPT_VERSION,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


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
    dialogue_context = _format_dialogue_context(snapshot)
    if not snapshot.course_count and not dialogue_context:
        return _save_public_profile(
            db,
            user.id,
            PUBLIC_PROFILE_NO_DATA_MESSAGE,
            _public_profile_source_snapshot(snapshot, "no_data"),
        )
    content = _generate_profile_content(
        user=user,
        snapshot=snapshot,
        api_key=USER_PROFILE_API_KEY,
        base_url=USER_PROFILE_BASE_URL,
        model=USER_PROFILE_MODEL,
        prompt_type="public",
    )
    basis = "academic_and_dialogue" if snapshot.course_count else "dialogue_only"
    if basis == "dialogue_only":
        content = f"{PUBLIC_PROFILE_DIALOGUE_ONLY_PREFIX}\n\n{content}"
    return _save_public_profile(
        db,
        user.id,
        content,
        _public_profile_source_snapshot(snapshot, basis),
    )


def fetch_system_profile(db: Session, user_id: int) -> UserSystemProfile | None:
    return db.query(UserSystemProfile).filter(UserSystemProfile.user_id == user_id).first()


def fetch_public_profile(db: Session, user_id: int) -> UserPublicProfile | None:
    return db.query(UserPublicProfile).filter(UserPublicProfile.user_id == user_id).first()
