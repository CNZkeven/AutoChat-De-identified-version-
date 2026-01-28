from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_dm_schemas(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS dm"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ops"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS stg"))


def ensure_dm_rls(engine: Engine) -> None:
    policy_sql = """
DO $$
BEGIN
  IF to_regclass('dm.student_scores') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE dm.student_scores ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_student_scores ON dm.student_scores';
    EXECUTE 'CREATE POLICY p_dm_student_scores ON dm.student_scores FOR SELECT USING ('
            || 'student_no = current_setting(''app.student_no'', true) '
            || 'OR current_setting(''app.role'', true) IN (''admin'', ''sync'')' || ')';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_student_scores_write ON dm.student_scores';
    EXECUTE 'CREATE POLICY p_dm_student_scores_write ON dm.student_scores FOR ALL USING ('
            || 'current_setting(''app.role'', true) IN (''admin'', ''sync'')' || ') '
            || 'WITH CHECK (current_setting(''app.role'', true) IN (''admin'', ''sync''))';
  END IF;

  IF to_regclass('dm.enrollments') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE dm.enrollments ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_enrollments ON dm.enrollments';
    EXECUTE 'CREATE POLICY p_dm_enrollments ON dm.enrollments FOR SELECT USING ('
            || 'student_no = current_setting(''app.student_no'', true) '
            || 'OR current_setting(''app.role'', true) IN (''admin'', ''sync'')' || ')';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_enrollments_write ON dm.enrollments';
    EXECUTE 'CREATE POLICY p_dm_enrollments_write ON dm.enrollments FOR ALL USING ('
            || 'current_setting(''app.role'', true) IN (''admin'', ''sync'')' || ') '
            || 'WITH CHECK (current_setting(''app.role'', true) IN (''admin'', ''sync''))';
  END IF;

  IF to_regclass('dm.section_grade_summary') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE dm.section_grade_summary ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_section_grade_summary ON dm.section_grade_summary';
    EXECUTE 'CREATE POLICY p_dm_section_grade_summary ON dm.section_grade_summary FOR SELECT USING ('
            || 'current_setting(''app.role'', true) IN (''admin'', ''sync'') '
            || 'OR EXISTS (SELECT 1 FROM dm.enrollments e '
            || 'WHERE e.offering_id = dm.section_grade_summary.offering_id '
            || 'AND e.student_no = current_setting(''app.student_no'', true))' || ')';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_section_grade_summary_write ON dm.section_grade_summary';
    EXECUTE 'CREATE POLICY p_dm_section_grade_summary_write ON dm.section_grade_summary FOR ALL USING ('
            || 'current_setting(''app.role'', true) IN (''admin'', ''sync'')' || ') '
            || 'WITH CHECK (current_setting(''app.role'', true) IN (''admin'', ''sync''))';
  END IF;

  IF to_regclass('dm.student_objective_achievements') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE dm.student_objective_achievements ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_student_objective ON dm.student_objective_achievements';
    EXECUTE 'CREATE POLICY p_dm_student_objective ON dm.student_objective_achievements FOR SELECT USING ('
            || 'student_no = current_setting(''app.student_no'', true) '
            || 'OR current_setting(''app.role'', true) IN (''admin'', ''sync'')' || ')';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_student_objective_write ON dm.student_objective_achievements';
    EXECUTE 'CREATE POLICY p_dm_student_objective_write ON dm.student_objective_achievements FOR ALL USING ('
            || 'current_setting(''app.role'', true) IN (''admin'', ''sync'')' || ') '
            || 'WITH CHECK (current_setting(''app.role'', true) IN (''admin'', ''sync''))';
  END IF;

  IF to_regclass('dm.section_objective_summary') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE dm.section_objective_summary ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_section_objective_summary ON dm.section_objective_summary';
    EXECUTE 'CREATE POLICY p_dm_section_objective_summary ON dm.section_objective_summary FOR SELECT USING ('
            || 'current_setting(''app.role'', true) IN (''admin'', ''sync'') '
            || 'OR EXISTS (SELECT 1 FROM dm.enrollments e '
            || 'WHERE e.offering_id = dm.section_objective_summary.offering_id '
            || 'AND e.student_no = current_setting(''app.student_no'', true))' || ')';
    EXECUTE 'DROP POLICY IF EXISTS p_dm_section_objective_summary_write ON dm.section_objective_summary';
    EXECUTE 'CREATE POLICY p_dm_section_objective_summary_write ON dm.section_objective_summary FOR ALL USING ('
            || 'current_setting(''app.role'', true) IN (''admin'', ''sync'')' || ') '
            || 'WITH CHECK (current_setting(''app.role'', true) IN (''admin'', ''sync''))';
  END IF;
END $$;
"""
    with engine.begin() as conn:
        conn.execute(text(policy_sql))
