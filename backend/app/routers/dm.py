from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User

router = APIRouter(prefix="/api/dm", tags=["dm"])


def _set_dm_context(db: Session, student_no: str) -> None:
    db.execute(
        text("SELECT set_config('app.student_no', :student_no, true)"),
        {"student_no": student_no},
    )
    db.execute(text("SELECT set_config('app.role', 'student', true)"))


@router.get("/me/sections")
def list_my_sections(
    term: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    _set_dm_context(db, current_user.username)
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
 ORDER BY t.term_name DESC NULLS LAST, c.course_code ASC
"""
    rows = db.execute(
        text(sql), {"student_no": current_user.username, "term": term}
    ).mappings().all()
    return {"items": [dict(row) for row in rows]}


@router.get("/me/scores")
def list_my_scores(
    term: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    _set_dm_context(db, current_user.username)
    sql = """
SELECT s.offering_id,
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
 ORDER BY t.term_name DESC NULLS LAST, c.course_code ASC
"""
    rows = db.execute(
        text(sql), {"student_no": current_user.username, "term": term}
    ).mappings().all()
    return {"items": [dict(row) for row in rows]}


@router.get("/me/sections/{offering_id}/summary")
def get_section_summary(
    offering_id: int,
    min_sample: int = Query(default=10, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    _set_dm_context(db, current_user.username)
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
    row = db.execute(text(sql), {"offering_id": offering_id}).mappings().first()
    if not row:
        return {"status": "not_found", "offering_id": offering_id}
    payload = dict(row)
    if payload.get("n_students") is not None and payload["n_students"] < min_sample:
        payload["note"] = "insufficient_sample"
    return payload
