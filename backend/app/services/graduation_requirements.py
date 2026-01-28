from __future__ import annotations

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


def _fetch_requirements(db: Session, program_id: int) -> list[dict[str, Any]]:
    sql = """
SELECT requirement_id AS id,
       requirement_index AS index,
       description,
       level,
       parent_id,
       training_program_version_id
  FROM dm.graduation_requirements
 WHERE program_id = :program_id
 ORDER BY level ASC NULLS LAST, requirement_index ASC NULLS LAST
"""
    rows = db.execute(text(sql), {"program_id": program_id}).mappings().all()
    return [dict(row) for row in rows]


def _fetch_requirement_mappings(db: Session, program_id: int) -> list[dict[str, Any]]:
    sql = """
SELECT orm.objective_id, orm.requirement_id
  FROM dm.objective_requirement_mapping orm
  JOIN dm.graduation_requirements gr ON gr.requirement_id = orm.requirement_id
 WHERE gr.program_id = :program_id
"""
    rows = db.execute(text(sql), {"program_id": program_id}).mappings().all()
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
        return {
            "program_id": None,
            "requirements": [],
            "summary": {"total": 0, "achieved": 0, "threshold": ACHIEVEMENT_THRESHOLD},
        }

    requirements = _fetch_requirements(db, program_id)
    mappings = _fetch_requirement_mappings(db, program_id)
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
            }
        )

    return {
        "program_id": program_id,
        "requirements": result_requirements,
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
