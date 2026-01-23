from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text

from ..config import ACHIEVE_DB_DSN, DATABASE_URL, SYNC_BATCH_SIZE, SYNC_TERM_WINDOW
from ..db import Base
from ..services.dm_bootstrap import ensure_dm_rls, ensure_dm_schemas

logger = logging.getLogger(__name__)

SOURCE_NAME = "achieve"


def _parse_term_window(term_window: str | None) -> list[str] | None:
    if not term_window:
        return []
    if isinstance(term_window, str):
        terms = [term.strip() for term in term_window.split(",") if term.strip()]
        return terms or []
    return []


def _get_watermark(conn, entity_name: str) -> datetime | None:
    row = conn.execute(
        text(
            """
SELECT last_updated_at
  FROM ops.sync_watermark
 WHERE source_name = :source_name
   AND entity_name = :entity_name
"""
        ),
        {"source_name": SOURCE_NAME, "entity_name": entity_name},
    ).first()
    return row[0] if row else None


def _update_watermark(conn, entity_name: str, updated_at: datetime | None) -> None:
    conn.execute(
        text(
            """
INSERT INTO ops.sync_watermark(source_name, entity_name, last_updated_at, updated_at)
VALUES (:source_name, :entity_name, :last_updated_at, now())
ON CONFLICT (source_name, entity_name)
DO UPDATE SET last_updated_at = EXCLUDED.last_updated_at, updated_at = now()
"""
        ),
        {
            "source_name": SOURCE_NAME,
            "entity_name": entity_name,
            "last_updated_at": updated_at,
        },
    )


def _write_job_log(conn, job_id: str, job_name: str, status: str, detail: dict[str, Any]) -> None:
    detail_payload = json.dumps(detail, default=str, ensure_ascii=False)
    conn.execute(
        text(
            """
INSERT INTO ops.sync_job_log(job_id, job_name, started_at, finished_at, status, detail)
VALUES (:job_id, :job_name, :started_at, :finished_at, :status, :detail)
ON CONFLICT (job_id) DO UPDATE
SET finished_at = EXCLUDED.finished_at,
    status = EXCLUDED.status,
    detail = EXCLUDED.detail
"""
        ),
        {
            "job_id": job_id,
            "job_name": job_name,
            "started_at": detail.get("started_at"),
            "finished_at": detail.get("finished_at"),
            "status": status,
            "detail": detail_payload,
        },
    )


def _chunked(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def _fetch_rows(conn, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    result = conn.execute(text(sql), params).mappings().all()
    return [dict(row) for row in result]


def _sync_students(achieve_conn, local_conn, batch_size: int) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "students")
    params = {"updated_after": last_updated}
    sql = """
SELECT id AS student_id,
       student_id_number AS student_no,
       full_name,
       program_id,
       grade_id,
       class_name,
       updated_at
  FROM students
 WHERE updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.students(
    student_id, student_no, full_name, program_id, grade_id, class_name, updated_at
) VALUES (
    :student_id, :student_no, :full_name, :program_id, :grade_id, :class_name, :updated_at
)
ON CONFLICT (student_id) DO UPDATE
SET student_no = EXCLUDED.student_no,
    full_name = EXCLUDED.full_name,
    program_id = EXCLUDED.program_id,
    grade_id = EXCLUDED.grade_id,
    class_name = EXCLUDED.class_name,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_programs(achieve_conn, local_conn, batch_size: int) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "programs")
    params = {"updated_after": last_updated}
    sql = """
SELECT id AS program_id,
       program_code,
       name,
       updated_at
  FROM programs
 WHERE updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.programs(program_id, program_code, name, updated_at)
VALUES (:program_id, :program_code, :name, :updated_at)
ON CONFLICT (program_id) DO UPDATE
SET program_code = EXCLUDED.program_code,
    name = EXCLUDED.name,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_program_versions(achieve_conn, local_conn, batch_size: int) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "program_versions")
    params = {"updated_after": last_updated}
    sql = """
SELECT id AS program_version_id,
       program_id,
       version_name,
       description,
       is_active,
       updated_at
  FROM training_program_versions
 WHERE updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.program_versions(
    program_version_id, program_id, version_name, description, is_active, updated_at
) VALUES (
    :program_version_id, :program_id, :version_name, :description, :is_active, :updated_at
)
ON CONFLICT (program_version_id) DO UPDATE
SET program_id = EXCLUDED.program_id,
    version_name = EXCLUDED.version_name,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_program_version_courses(achieve_conn, local_conn, batch_size: int) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "program_version_courses")
    params = {"updated_after": last_updated}
    sql = """
SELECT training_program_version_id AS program_version_id,
       course_id,
       course_category,
       course_nature,
       planned_semester,
       plan_remarks,
       display_order_label,
       display_order_primary,
       display_order_secondary,
       updated_at
  FROM program_version_courses
 WHERE updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.program_version_courses(
    program_version_id, course_id, course_category, course_nature, planned_semester,
    plan_remarks, display_order_label, display_order_primary, display_order_secondary, updated_at
) VALUES (
    :program_version_id, :course_id, :course_category, :course_nature, :planned_semester,
    :plan_remarks, :display_order_label, :display_order_primary, :display_order_secondary, :updated_at
)
ON CONFLICT (program_version_id, course_id) DO UPDATE
SET course_category = EXCLUDED.course_category,
    course_nature = EXCLUDED.course_nature,
    planned_semester = EXCLUDED.planned_semester,
    plan_remarks = EXCLUDED.plan_remarks,
    display_order_label = EXCLUDED.display_order_label,
    display_order_primary = EXCLUDED.display_order_primary,
    display_order_secondary = EXCLUDED.display_order_secondary,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_courses(achieve_conn, local_conn, batch_size: int) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "courses")
    params = {"updated_after": last_updated}
    sql = """
SELECT id AS course_id,
       course_code,
       name AS course_name,
       credits,
       total_hours,
       lecture_hours,
       experiment_hours,
       practice_hours,
       updated_at
  FROM courses
 WHERE updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.courses(
    course_id, course_code, course_name, credits, total_hours,
    lecture_hours, experiment_hours, practice_hours, updated_at
) VALUES (
    :course_id, :course_code, :course_name, :credits, :total_hours,
    :lecture_hours, :experiment_hours, :practice_hours, :updated_at
)
ON CONFLICT (course_id) DO UPDATE
SET course_code = EXCLUDED.course_code,
    course_name = EXCLUDED.course_name,
    credits = EXCLUDED.credits,
    total_hours = EXCLUDED.total_hours,
    lecture_hours = EXCLUDED.lecture_hours,
    experiment_hours = EXCLUDED.experiment_hours,
    practice_hours = EXCLUDED.practice_hours,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_terms(achieve_conn, local_conn, batch_size: int, terms: list[str] | None) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "academic_terms")
    params = {"updated_after": last_updated, "terms": terms}
    sql = """
SELECT id AS term_id,
       name AS term_name,
       start_year,
       end_year,
       term_index,
       updated_at
  FROM academic_terms
 WHERE updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
   AND (cardinality(CAST(:terms AS text[])) = 0 OR name = ANY(CAST(:terms AS text[])))
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.academic_terms(
    term_id, term_name, start_year, end_year, term_index, updated_at
) VALUES (
    :term_id, :term_name, :start_year, :end_year, :term_index, :updated_at
)
ON CONFLICT (term_id) DO UPDATE
SET term_name = EXCLUDED.term_name,
    start_year = EXCLUDED.start_year,
    end_year = EXCLUDED.end_year,
    term_index = EXCLUDED.term_index,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_course_offerings(
    achieve_conn,
    local_conn,
    batch_size: int,
    terms: list[str] | None,
) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "course_offerings")
    params = {"updated_after": last_updated, "terms": terms}
    sql = """
SELECT o.id AS offering_id,
       o.course_id,
       o.term_id,
       o.teacher_id,
       u.full_name AS teacher_name,
       o.section_name,
       o.class_number,
       o.program_id,
       o.grade_year,
       o.updated_at
  FROM course_offerings o
  LEFT JOIN users u ON u.id = o.teacher_id
  JOIN academic_terms t ON t.id = o.term_id
 WHERE o.updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
   AND (cardinality(CAST(:terms AS text[])) = 0 OR t.name = ANY(CAST(:terms AS text[])))
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.course_offerings(
    offering_id, course_id, term_id, teacher_id, teacher_name,
    section_name, class_number, program_id, grade_year, updated_at
) VALUES (
    :offering_id, :course_id, :term_id, :teacher_id, :teacher_name,
    :section_name, :class_number, :program_id, :grade_year, :updated_at
)
ON CONFLICT (offering_id) DO UPDATE
SET course_id = EXCLUDED.course_id,
    term_id = EXCLUDED.term_id,
    teacher_id = EXCLUDED.teacher_id,
    teacher_name = EXCLUDED.teacher_name,
    section_name = EXCLUDED.section_name,
    class_number = EXCLUDED.class_number,
    program_id = EXCLUDED.program_id,
    grade_year = EXCLUDED.grade_year,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_enrollments(
    achieve_conn,
    local_conn,
    batch_size: int,
    terms: list[str] | None,
) -> dict[str, Any]:
    sql = """
SELECT e.offering_id,
       e.student_id,
       s.student_id_number AS student_no,
       e.enrolled_at
  FROM enrollments e
  JOIN students s ON s.id = e.student_id
  JOIN course_offerings o ON o.id = e.offering_id
  JOIN academic_terms t ON t.id = o.term_id
 WHERE (cardinality(CAST(:terms AS text[])) = 0 OR t.name = ANY(CAST(:terms AS text[])))
"""
    rows = _fetch_rows(achieve_conn, sql, {"terms": terms})
    if not rows:
        return {"rows": 0, "updated_at": None}
    for row in rows:
        row["updated_at"] = row.get("enrolled_at")
    insert_sql = text(
        """
INSERT INTO dm.enrollments(
    offering_id, student_id, student_no, enrolled_at, updated_at
) VALUES (
    :offering_id, :student_id, :student_no, :enrolled_at, :updated_at
)
ON CONFLICT (offering_id, student_id) DO UPDATE
SET student_no = EXCLUDED.student_no,
    enrolled_at = EXCLUDED.enrolled_at,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    return {"rows": len(rows), "updated_at": None}


def _sync_student_scores(
    achieve_conn,
    local_conn,
    batch_size: int,
    terms: list[str] | None,
) -> dict[str, Any]:
    sql = """
WITH base AS (
    SELECT e.offering_id,
           e.student_id,
           s.student_id_number AS student_no,
           r.official_score,
           r.official_score_text,
           r.updated_at AS remark_updated_at
      FROM enrollments e
      JOIN students s ON s.id = e.student_id
      LEFT JOIN student_remarks r ON r.offering_id = e.offering_id AND r.student_id = e.student_id
      JOIN course_offerings o ON o.id = e.offering_id
      JOIN academic_terms t ON t.id = o.term_id
     WHERE (cardinality(CAST(:terms AS text[])) = 0 OR t.name = ANY(CAST(:terms AS text[])))
),
calc AS (
    SELECT student_id,
           offering_id,
           MAX(score) FILTER (WHERE lower(category_type) IN ('total','final','overall')) AS calc_score,
           MAX(updated_at) AS calc_updated_at
      FROM student_calculated_grades
     GROUP BY student_id, offering_id
)
SELECT base.offering_id,
       base.student_id,
       base.student_no,
       COALESCE(base.official_score, calc.calc_score) AS total_score,
       base.official_score_text AS grade_text,
       CASE
         WHEN base.official_score IS NOT NULL THEN 'official'
         WHEN calc.calc_score IS NOT NULL THEN 'calculated'
         ELSE NULL
       END AS score_source,
       GREATEST(
           COALESCE(base.remark_updated_at, 'epoch'::timestamptz),
           COALESCE(calc.calc_updated_at, 'epoch'::timestamptz)
       ) AS updated_at
  FROM base
  LEFT JOIN calc ON calc.student_id = base.student_id AND calc.offering_id = base.offering_id
 WHERE COALESCE(base.official_score, calc.calc_score) IS NOT NULL
"""
    rows = _fetch_rows(achieve_conn, sql, {"terms": terms})
    if not rows:
        return {"rows": 0, "updated_at": None}
    insert_sql = text(
        """
INSERT INTO dm.student_scores(
    offering_id, student_id, student_no, total_score, grade_text, score_source, updated_at
) VALUES (
    :offering_id, :student_id, :student_no, :total_score, :grade_text, :score_source, :updated_at
)
ON CONFLICT (offering_id, student_id) DO UPDATE
SET total_score = EXCLUDED.total_score,
    grade_text = EXCLUDED.grade_text,
    score_source = EXCLUDED.score_source,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_syllabus_versions(achieve_conn, local_conn, batch_size: int) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "syllabus_versions")
    params = {"updated_after": last_updated}
    sql = """
SELECT id AS syllabus_version_id,
       course_id,
       version_name,
       description,
       is_active,
       is_default,
       syllabus_type,
       status,
       basic_info,
       process_requirements,
       updated_at
  FROM syllabus_versions
 WHERE updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.syllabus_versions(
    syllabus_version_id, course_id, version_name, description, is_active,
    is_default, syllabus_type, status, basic_info, process_requirements, updated_at
) VALUES (
    :syllabus_version_id, :course_id, :version_name, :description, :is_active,
    :is_default, :syllabus_type, :status, :basic_info, :process_requirements, :updated_at
)
ON CONFLICT (syllabus_version_id) DO UPDATE
SET course_id = EXCLUDED.course_id,
    version_name = EXCLUDED.version_name,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    is_default = EXCLUDED.is_default,
    syllabus_type = EXCLUDED.syllabus_type,
    status = EXCLUDED.status,
    basic_info = EXCLUDED.basic_info,
    process_requirements = EXCLUDED.process_requirements,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_course_objectives(achieve_conn, local_conn, batch_size: int) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "course_objectives")
    params = {"updated_after": last_updated}
    sql = """
SELECT co.id AS objective_id,
       co.offering_id,
       co.syllabus_version_id,
       co.index AS objective_index,
       co.description,
       co.type AS objective_type,
       co.updated_at,
       sv.course_id
  FROM course_objectives co
  LEFT JOIN syllabus_versions sv ON sv.id = co.syllabus_version_id
 WHERE co.updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.course_objectives(
    objective_id, course_id, offering_id, syllabus_version_id,
    objective_index, description, objective_type, updated_at
) VALUES (
    :objective_id, :course_id, :offering_id, :syllabus_version_id,
    :objective_index, :description, :objective_type, :updated_at
)
ON CONFLICT (objective_id) DO UPDATE
SET course_id = EXCLUDED.course_id,
    offering_id = EXCLUDED.offering_id,
    syllabus_version_id = EXCLUDED.syllabus_version_id,
    objective_index = EXCLUDED.objective_index,
    description = EXCLUDED.description,
    objective_type = EXCLUDED.objective_type,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _sync_objective_achievements(
    achieve_conn,
    local_conn,
    batch_size: int,
    terms: list[str] | None,
) -> dict[str, Any]:
    last_updated = _get_watermark(local_conn, "objective_achievements")
    params = {"updated_after": last_updated, "terms": terms}
    sql = """
SELECT oa.offering_id,
       oa.student_id,
       s.student_id_number AS student_no,
       oa.objective_id,
       oa."achievementScore" AS achievement_score,
       oa."totalScore" AS total_score,
       oa."maxScore" AS max_score,
       oa.updated_at
  FROM objective_achievements oa
  JOIN students s ON s.id = oa.student_id
  JOIN course_offerings o ON o.id = oa.offering_id
  JOIN academic_terms t ON t.id = o.term_id
 WHERE oa.updated_at > COALESCE(:updated_after, 'epoch'::timestamptz)
   AND (cardinality(CAST(:terms AS text[])) = 0 OR t.name = ANY(CAST(:terms AS text[])))
"""
    rows = _fetch_rows(achieve_conn, sql, params)
    if not rows:
        return {"rows": 0, "updated_at": last_updated}
    insert_sql = text(
        """
INSERT INTO dm.student_objective_achievements(
    offering_id, student_id, objective_id, student_no,
    achievement_score, total_score, max_score, updated_at
) VALUES (
    :offering_id, :student_id, :objective_id, :student_no,
    :achievement_score, :total_score, :max_score, :updated_at
)
ON CONFLICT (offering_id, student_id, objective_id) DO UPDATE
SET achievement_score = EXCLUDED.achievement_score,
    total_score = EXCLUDED.total_score,
    max_score = EXCLUDED.max_score,
    student_no = EXCLUDED.student_no,
    updated_at = EXCLUDED.updated_at
"""
    )
    for chunk in _chunked(rows, batch_size):
        local_conn.execute(insert_sql, chunk)
    max_updated = max(row["updated_at"] for row in rows if row.get("updated_at"))
    return {"rows": len(rows), "updated_at": max_updated}


def _recompute_section_grade_summary(local_conn, terms: list[str] | None) -> dict[str, Any]:
    params = {"terms": terms}
    sql = """
INSERT INTO dm.section_grade_summary(
    offering_id, term_id, n_students, avg_score, min_score, max_score, dist_json, computed_at
)
SELECT o.offering_id,
       o.term_id,
       COUNT(*)::int AS n_students,
       AVG(s.total_score)::numeric(5,2) AS avg_score,
       MIN(s.total_score)::numeric(5,2) AS min_score,
       MAX(s.total_score)::numeric(5,2) AS max_score,
       jsonb_build_object(
           '0-59',  SUM(CASE WHEN s.total_score < 60 THEN 1 ELSE 0 END),
           '60-69', SUM(CASE WHEN s.total_score >= 60 AND s.total_score < 70 THEN 1 ELSE 0 END),
           '70-79', SUM(CASE WHEN s.total_score >= 70 AND s.total_score < 80 THEN 1 ELSE 0 END),
           '80-89', SUM(CASE WHEN s.total_score >= 80 AND s.total_score < 90 THEN 1 ELSE 0 END),
           '90-100', SUM(CASE WHEN s.total_score >= 90 THEN 1 ELSE 0 END)
       ) AS dist_json,
       now()
  FROM dm.student_scores s
  JOIN dm.course_offerings o ON o.offering_id = s.offering_id
  JOIN dm.academic_terms t ON t.term_id = o.term_id
 WHERE s.total_score IS NOT NULL
   AND (cardinality(CAST(:terms AS text[])) = 0 OR t.term_name = ANY(CAST(:terms AS text[])))
 GROUP BY o.offering_id, o.term_id
ON CONFLICT (offering_id) DO UPDATE
SET n_students = EXCLUDED.n_students,
    avg_score = EXCLUDED.avg_score,
    min_score = EXCLUDED.min_score,
    max_score = EXCLUDED.max_score,
    dist_json = EXCLUDED.dist_json,
    term_id = EXCLUDED.term_id,
    computed_at = now()
"""
    local_conn.execute(text(sql), params)
    return {"status": "ok"}


def _recompute_section_objective_summary(local_conn, terms: list[str] | None) -> dict[str, Any]:
    params = {"terms": terms}
    sql = """
INSERT INTO dm.section_objective_summary(
    offering_id, objective_id, n_students, avg_score, min_score, max_score, computed_at
)
SELECT oa.offering_id,
       oa.objective_id,
       COUNT(*)::int AS n_students,
       AVG(oa.achievement_score)::numeric(5,4) AS avg_score,
       MIN(oa.achievement_score)::numeric(5,4) AS min_score,
       MAX(oa.achievement_score)::numeric(5,4) AS max_score,
       now()
  FROM dm.student_objective_achievements oa
  JOIN dm.course_offerings o ON o.offering_id = oa.offering_id
  JOIN dm.academic_terms t ON t.term_id = o.term_id
 WHERE (cardinality(CAST(:terms AS text[])) = 0 OR t.term_name = ANY(CAST(:terms AS text[])))
 GROUP BY oa.offering_id, oa.objective_id
ON CONFLICT (offering_id, objective_id) DO UPDATE
SET n_students = EXCLUDED.n_students,
    avg_score = EXCLUDED.avg_score,
    min_score = EXCLUDED.min_score,
    max_score = EXCLUDED.max_score,
    computed_at = now()
"""
    local_conn.execute(text(sql), params)
    return {"status": "ok"}


def run_dm_sync(
    job_name: str = "dm_sync",
    entities: list[str] | None = None,
    term_window: list[str] | None = None,
    batch_size: int | None = None,
) -> dict[str, Any]:
    if not ACHIEVE_DB_DSN:
        raise RuntimeError("ACHIEVE_DB_DSN is not configured")

    terms = term_window if term_window is not None else _parse_term_window(SYNC_TERM_WINDOW)
    batch = batch_size or SYNC_BATCH_SIZE

    local_engine = create_engine(DATABASE_URL)
    achieve_engine = create_engine(ACHIEVE_DB_DSN)

    ensure_dm_schemas(local_engine)
    Base.metadata.create_all(bind=local_engine)
    ensure_dm_rls(local_engine)

    job_id = str(uuid.uuid4())
    started_at = datetime.utcnow()
    detail: dict[str, Any] = {"started_at": started_at, "terms": terms, "entities": entities or []}

    with local_engine.begin() as local_conn:
        _write_job_log(local_conn, job_id, job_name, "RUNNING", detail)

    entity_list = entities or [
        "students",
        "programs",
        "program_versions",
        "program_version_courses",
        "courses",
        "academic_terms",
        "course_offerings",
        "enrollments",
        "student_scores",
        "syllabus_versions",
        "course_objectives",
        "objective_achievements",
    ]

    try:
        with achieve_engine.connect() as achieve_conn, local_engine.begin() as local_conn:
            local_conn.execute(text("SET LOCAL app.role = 'sync'"))
            for entity in entity_list:
                if entity == "students":
                    result = _sync_students(achieve_conn, local_conn, batch)
                elif entity == "programs":
                    result = _sync_programs(achieve_conn, local_conn, batch)
                elif entity == "program_versions":
                    result = _sync_program_versions(achieve_conn, local_conn, batch)
                elif entity == "program_version_courses":
                    result = _sync_program_version_courses(achieve_conn, local_conn, batch)
                elif entity == "courses":
                    result = _sync_courses(achieve_conn, local_conn, batch)
                elif entity == "academic_terms":
                    result = _sync_terms(achieve_conn, local_conn, batch, terms)
                elif entity == "course_offerings":
                    result = _sync_course_offerings(achieve_conn, local_conn, batch, terms)
                elif entity == "enrollments":
                    result = _sync_enrollments(achieve_conn, local_conn, batch, terms)
                elif entity == "student_scores":
                    result = _sync_student_scores(achieve_conn, local_conn, batch, terms)
                elif entity == "syllabus_versions":
                    result = _sync_syllabus_versions(achieve_conn, local_conn, batch)
                elif entity == "course_objectives":
                    result = _sync_course_objectives(achieve_conn, local_conn, batch)
                elif entity == "objective_achievements":
                    result = _sync_objective_achievements(achieve_conn, local_conn, batch, terms)
                else:
                    raise ValueError(f"unsupported entity: {entity}")

                detail[entity] = result
                if result.get("updated_at"):
                    _update_watermark(local_conn, entity, result["updated_at"])

            detail["section_grade_summary"] = _recompute_section_grade_summary(local_conn, terms)
            detail["section_objective_summary"] = _recompute_section_objective_summary(local_conn, terms)

    except Exception as exc:
        logger.exception("DM sync failed")
        detail["error"] = str(exc)
        detail["finished_at"] = datetime.utcnow()
        with local_engine.begin() as local_conn:
            _write_job_log(local_conn, job_id, job_name, "FAILED", detail)
        raise

    detail["finished_at"] = datetime.utcnow()
    with local_engine.begin() as local_conn:
        _write_job_log(local_conn, job_id, job_name, "SUCCESS", detail)

    return {
        "job_id": job_id,
        "job_name": job_name,
        "status": "SUCCESS",
        "detail": detail,
    }
