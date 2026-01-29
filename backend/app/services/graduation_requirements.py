from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import User, UserGraduationRequirementSnapshot
from ..services.academics import set_dm_role

ACHIEVEMENT_THRESHOLD = 0.67


def _fetch_program_id(db: Session, student_no: str) -> dict[str, Any]:
    set_dm_role(db, "admin")
    sql = """
SELECT student_id, program_id, grade_id
  FROM dm.students
 WHERE student_no = :student_no
"""
    row = db.execute(text(sql), {"student_no": student_no}).mappings().first()
    return dict(row) if row else {}


def _fetch_program_id_by_major(db: Session, major: str | None) -> int | None:
    if not major:
        return None
    sql = """
SELECT program_id
  FROM dm.programs
 WHERE name ILIKE :major
 ORDER BY length(name) DESC
 LIMIT 1
"""
    row = db.execute(text(sql), {"major": f"%{major}%"}).mappings().first()
    return int(row["program_id"]) if row else None


def _fetch_program_versions(db: Session, program_id: int) -> list[dict[str, Any]]:
    sql = """
SELECT program_version_id,
       version_name,
       updated_at,
       is_active
  FROM dm.program_versions
 WHERE program_id = :program_id
 ORDER BY is_active DESC, updated_at DESC NULLS LAST
"""
    rows = db.execute(text(sql), {"program_id": program_id}).mappings().all()
    return [dict(row) for row in rows]


def _extract_version_year(version_name: str | None) -> int | None:
    if not version_name:
        return None
    match = re.search(r"(20\d{2})", version_name)
    return int(match.group(1)) if match else None


def _select_program_version(versions: list[dict[str, Any]], grade_year: int | None) -> dict[str, Any] | None:
    if not versions:
        return None
    candidates = []
    if grade_year:
        for version in versions:
            year = _extract_version_year(version.get("version_name"))
            if year is not None and year <= grade_year:
                candidates.append({**version, "_version_year": year})
    selected_pool = candidates or versions

    def sort_key(item: dict[str, Any]) -> tuple[int, datetime]:
        year = item.get("_version_year")
        if year is None:
            year = _extract_version_year(item.get("version_name")) or -1
        updated_at = item.get("updated_at") or datetime.min
        return (year, updated_at)

    return max(selected_pool, key=sort_key)


def _fetch_requirements(
    db: Session, program_id: int, program_version_id: int | None
) -> list[dict[str, Any]]:
    sql = """
SELECT requirement_id AS id,
       requirement_index AS index,
       description,
       level,
       parent_id,
       training_program_version_id
  FROM dm.graduation_requirements
 WHERE program_id = :program_id
   AND (:program_version_id IS NULL OR training_program_version_id = :program_version_id)
 ORDER BY level ASC NULLS LAST, requirement_index ASC NULLS LAST
"""
    rows = db.execute(
        text(sql), {"program_id": program_id, "program_version_id": program_version_id}
    ).mappings().all()
    return [dict(row) for row in rows]


def _fetch_requirement_mappings(
    db: Session, program_id: int, program_version_id: int | None
) -> list[dict[str, Any]]:
    sql = """
SELECT orm.objective_id, orm.requirement_id
  FROM dm.objective_requirement_mapping orm
  JOIN dm.graduation_requirements gr ON gr.requirement_id = orm.requirement_id
 WHERE gr.program_id = :program_id
   AND (:program_version_id IS NULL OR gr.training_program_version_id = :program_version_id)
"""
    rows = db.execute(
        text(sql), {"program_id": program_id, "program_version_id": program_version_id}
    ).mappings().all()
    return [dict(row) for row in rows]


def _fetch_student_objective_scores(db: Session, student_no: str) -> list[dict[str, Any]]:
    set_dm_role(db, "admin")
    sql = """
SELECT objective_id, achievement_score
  FROM dm.student_objective_achievements
 WHERE student_no = :student_no
"""
    rows = db.execute(text(sql), {"student_no": student_no}).mappings().all()
    return [dict(row) for row in rows]


def build_requirement_snapshot(db: Session, user: User) -> dict[str, Any]:
    student_no = user.username
    meta = _fetch_program_id(db, student_no)
    program_id = meta.get("program_id")
    if not program_id:
        program_id = _fetch_program_id_by_major(db, user.major)
    if not program_id:
        return {
            "program_id": None,
            "program_version_id": None,
            "program_version_year": None,
            "requirements": [],
            "requirements_grouped": [],
            "summary": {"total": 0, "achieved": 0, "threshold": ACHIEVEMENT_THRESHOLD},
        }

    versions = _fetch_program_versions(db, program_id)
    selected_version = _select_program_version(versions, user.grade)
    program_version_id = (
        int(selected_version["program_version_id"]) if selected_version else None
    )
    program_version_year = (
        _extract_version_year(selected_version.get("version_name")) if selected_version else None
    )

    requirements = _fetch_requirements(db, program_id, program_version_id)
    mappings = _fetch_requirement_mappings(db, program_id, program_version_id)
    student_scores = _fetch_student_objective_scores(db, student_no)

    score_map: dict[int, list[float]] = {}
    for item in student_scores:
        objective_id = item.get("objective_id")
        score = item.get("achievement_score")
        if objective_id is None or score is None:
            continue
        score_map.setdefault(int(objective_id), []).append(float(score))

    requirement_objectives: dict[int, list[int]] = {}
    for mapping in mappings:
        requirement_id = mapping.get("requirement_id")
        objective_id = mapping.get("objective_id")
        if requirement_id is None or objective_id is None:
            continue
        requirement_objectives.setdefault(int(requirement_id), []).append(int(objective_id))

    result_requirements = []
    achieved_count = 0
    for req in requirements:
        req_id = int(req["id"])
        objective_ids = requirement_objectives.get(req_id, [])
        collected_scores = []
        for obj_id in objective_ids:
            collected_scores.extend(score_map.get(obj_id, []))
        achievement_rate = sum(collected_scores) / len(collected_scores) if collected_scores else None
        achieved = achievement_rate is not None and achievement_rate >= ACHIEVEMENT_THRESHOLD
        if achieved:
            achieved_count += 1
        result_requirements.append(
            {
                "id": req_id,
                "index": req.get("index"),
                "description": req.get("description"),
                "level": req.get("level"),
                "parent_id": req.get("parent_id"),
                "achievement_rate": achievement_rate,
                "achieved": achieved,
                "objective_count": len(objective_ids),
                "covered_objectives": len(collected_scores),
                "children": [],
            }
        )

    requirement_map = {item["id"]: item for item in result_requirements}
    grouped_requirements = []
    for item in result_requirements:
        parent_id = item.get("parent_id")
        if parent_id is not None and parent_id in requirement_map:
            requirement_map[parent_id]["children"].append(item)
        else:
            grouped_requirements.append(item)

    return {
        "program_id": program_id,
        "program_version_id": program_version_id,
        "program_version_year": program_version_year,
        "requirements": result_requirements,
        "requirements_grouped": grouped_requirements,
        "summary": {
            "total": len(result_requirements),
            "achieved": achieved_count,
            "threshold": ACHIEVEMENT_THRESHOLD,
        },
    }


def get_or_refresh_snapshot(db: Session, user: User, force_refresh: bool = False) -> UserGraduationRequirementSnapshot:
    existing = (
        db.query(UserGraduationRequirementSnapshot)
        .filter(UserGraduationRequirementSnapshot.user_id == user.id)
        .first()
    )
    if existing and not force_refresh:
        return existing

    data = build_requirement_snapshot(db, user)
    source_snapshot = {
        "generated_at": datetime.utcnow().isoformat(),
        "program_id": data.get("program_id"),
        "program_version_id": data.get("program_version_id"),
    }

    if existing:
        existing.program_id = data.get("program_id")
        existing.grade_year = user.grade
        existing.data = data
        existing.source_snapshot = source_snapshot
        db.commit()
        db.refresh(existing)
        return existing

    snapshot = UserGraduationRequirementSnapshot(
        user_id=user.id,
        program_id=data.get("program_id"),
        grade_year=user.grade,
        data=data,
        source_snapshot=source_snapshot,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
