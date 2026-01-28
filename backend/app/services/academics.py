from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_dm_role(db: Session, role: str, student_no: str | None = None) -> None:
    db.execute(text("SELECT set_config('app.role', :role, true)"), {"role": role})
    if student_no is not None:
        db.execute(
            text("SELECT set_config('app.student_no', :student_no, true)"),
            {"student_no": student_no},
        )


def list_student_courses(db: Session, student_no: str, role: str = "student") -> list[dict[str, Any]]:
    set_dm_role(db, role, student_no if role != "admin" else None)
    sql = """
WITH base AS (
    SELECT e.offering_id,
           o.teacher_name,
           o.class_number,
           c.course_code,
           c.course_name,
           t.term_name,
           t.start_year AS term_start_year,
           t.term_index
      FROM dm.enrollments e
      JOIN dm.course_offerings o ON o.offering_id = e.offering_id
      JOIN dm.courses c ON c.course_id = o.course_id
      LEFT JOIN dm.academic_terms t ON t.term_id = o.term_id
     WHERE e.student_no = :student_no
       AND COALESCE(o.is_in_class_experiment, false) = false
),
score_base AS (
    SELECT s.offering_id,
           s.total_score,
           s.grade_text
      FROM dm.student_scores s
     WHERE s.student_no = :student_no
),
percentiles AS (
    SELECT offering_id,
           student_no,
           percent_rank() OVER (PARTITION BY offering_id ORDER BY total_score) AS percentile
      FROM dm.student_scores
     WHERE total_score IS NOT NULL
)
SELECT b.offering_id,
       b.class_number,
       b.course_code,
       b.course_name,
       b.teacher_name,
       s.total_score,
       s.grade_text,
       p.percentile
  FROM base b
  LEFT JOIN score_base s ON s.offering_id = b.offering_id
  LEFT JOIN percentiles p ON p.offering_id = b.offering_id AND p.student_no = :student_no
 ORDER BY b.term_start_year DESC NULLS LAST,
          b.term_index DESC NULLS LAST,
          b.class_number ASC NULLS LAST,
          b.course_code ASC
"""
    rows = db.execute(text(sql), {"student_no": student_no}).mappings().all()
    return [dict(row) for row in rows]


def list_course_objectives(
    db: Session,
    student_no: str,
    offering_id: int,
    role: str = "student",
) -> list[dict[str, Any]]:
    set_dm_role(db, role, student_no if role != "admin" else None)
    offering = db.execute(
        text(
            """
SELECT course_id,
       selected_syllabus_version_id,
       COALESCE(is_in_class_experiment, false) AS is_in_class_experiment
  FROM dm.course_offerings
 WHERE offering_id = :offering_id
"""
        ),
        {"offering_id": offering_id},
    ).mappings().first()
    if not offering or offering["is_in_class_experiment"]:
        return []

    course_id = offering["course_id"]
    selected_syllabus_version_id = offering["selected_syllabus_version_id"]

    def _extract_year(value: str | None) -> int | None:
        if not value:
            return None
        match = re.search(r"(20\\d{2})", value)
        return int(match.group(1)) if match else None

    def _resolve_program_version_id() -> int | None:
        student_row = db.execute(
            text(
                """
SELECT program_id, grade_year
  FROM dm.students
 WHERE student_no = :student_no
"""
            ),
            {"student_no": student_no},
        ).mappings().first()
        if not student_row:
            return None
        grade_year = student_row.get("grade_year")
        if grade_year is None:
            return None
        versions = db.execute(
            text(
                """
SELECT program_version_id, version_name, is_active
  FROM dm.program_versions
 WHERE program_id = :program_id
"""
            ),
            {"program_id": student_row["program_id"]},
        ).mappings().all()
        candidates: list[tuple[int, int, bool]] = []
        for row in versions:
            year = _extract_year(row.get("version_name"))
            if year is not None:
                candidates.append((year, row["program_version_id"], bool(row.get("is_active"))))
        eligible = [item for item in candidates if item[0] <= grade_year]
        if eligible:
            eligible.sort(key=lambda item: item[0], reverse=True)
            return eligible[0][1]
        active = [item for item in candidates if item[2]]
        if active:
            active.sort(key=lambda item: item[0], reverse=True)
            return active[0][1]
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]
        return None

    def _resolve_syllabus_version_id() -> int | None:
        if selected_syllabus_version_id is not None:
            return selected_syllabus_version_id
        program_version_id = _resolve_program_version_id()
        if program_version_id is not None:
            row = db.execute(
                text(
                    """
SELECT sv.syllabus_version_id
  FROM dm.syllabus_versions sv
  JOIN dm.syllabus_version_programs svp
    ON svp.syllabus_version_id = sv.syllabus_version_id
 WHERE sv.course_id = :course_id
   AND svp.training_program_version_id = :program_version_id
 ORDER BY sv.is_default DESC,
          sv.updated_at DESC NULLS LAST,
          sv.syllabus_version_id DESC
 LIMIT 1
"""
                ),
                {"course_id": course_id, "program_version_id": program_version_id},
            ).mappings().first()
            if row:
                return row["syllabus_version_id"]
        row = db.execute(
            text(
                """
SELECT syllabus_version_id
  FROM dm.syllabus_versions
 WHERE course_id = :course_id
 ORDER BY is_default DESC,
          updated_at DESC NULLS LAST,
          syllabus_version_id DESC
 LIMIT 1
"""
            ),
            {"course_id": course_id},
        ).mappings().first()
        return row["syllabus_version_id"] if row else None

    has_offering_objectives = db.execute(
        text("SELECT 1 FROM dm.course_objectives WHERE offering_id = :offering_id LIMIT 1"),
        {"offering_id": offering_id},
    ).first()
    target_syllabus_version_id = None if has_offering_objectives else _resolve_syllabus_version_id()

    if has_offering_objectives and selected_syllabus_version_id is not None:
        objective_filter = (
            "o.offering_id = :offering_id AND "
            "(o.syllabus_version_id IS NULL OR o.syllabus_version_id = :syllabus_version_id)"
        )
    elif has_offering_objectives:
        objective_filter = "o.offering_id = :offering_id"
    elif target_syllabus_version_id is not None:
        objective_filter = "o.course_id = :course_id AND o.syllabus_version_id = :syllabus_version_id"
    else:
        objective_filter = "o.course_id = :course_id"

    sql = f"""
WITH objectives AS (
    SELECT o.objective_id,
           o.objective_index,
           o.description
      FROM dm.course_objectives o
     WHERE {objective_filter}
),
student_scores AS (
    SELECT objective_id,
           achievement_score,
           total_score,
           max_score
      FROM dm.student_objective_achievements
     WHERE offering_id = :offering_id
       AND student_no = :student_no
),
percentiles AS (
    SELECT objective_id,
           student_no,
           percent_rank() OVER (PARTITION BY objective_id ORDER BY achievement_score) AS percentile
      FROM dm.student_objective_achievements
     WHERE offering_id = :offering_id
)
SELECT o.objective_id,
       o.objective_index,
       o.description,
       s.achievement_score,
       s.total_score,
       s.max_score,
       p.percentile
  FROM objectives o
  LEFT JOIN student_scores s ON s.objective_id = o.objective_id
  LEFT JOIN percentiles p ON p.objective_id = o.objective_id AND p.student_no = :student_no
 ORDER BY o.objective_index NULLS LAST, o.objective_id ASC
"""
    rows = db.execute(
        text(sql),
        {
            "student_no": student_no,
            "offering_id": offering_id,
            "course_id": course_id,
            "syllabus_version_id": target_syllabus_version_id or selected_syllabus_version_id,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def get_student_academic_updates(db: Session, student_no: str, role: str = "student") -> dict[str, Any]:
    set_dm_role(db, role, student_no if role != "admin" else None)
    sql = """
SELECT GREATEST(
    COALESCE((SELECT MAX(updated_at) FROM dm.enrollments WHERE student_no = :student_no), NULL),
    COALESCE((SELECT MAX(updated_at) FROM dm.student_scores WHERE student_no = :student_no), NULL),
    COALESCE((SELECT MAX(updated_at) FROM dm.student_objective_achievements WHERE student_no = :student_no), NULL)
) AS last_updated,
EXISTS (SELECT 1 FROM dm.enrollments WHERE student_no = :student_no) AS has_enrollments,
EXISTS (SELECT 1 FROM dm.student_scores WHERE student_no = :student_no) AS has_scores
"""
    row = db.execute(text(sql), {"student_no": student_no}).mappings().first()
    if not row:
        return {"last_updated": None, "has_enrollments": False, "has_scores": False}
    return dict(row)
