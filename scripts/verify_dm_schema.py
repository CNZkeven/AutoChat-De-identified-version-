import os

import psycopg


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='dm' AND table_name='course_offerings' AND column_name='is_in_class_experiment'
                """
            )
            if cur.fetchone() is None:
                raise AssertionError("missing dm.course_offerings.is_in_class_experiment")

            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='dm' AND table_name='course_offerings' AND column_name='selected_syllabus_version_id'
                """
            )
            if cur.fetchone() is None:
                raise AssertionError("missing dm.course_offerings.selected_syllabus_version_id")

            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='dm' AND table_name='students' AND column_name='grade_year'
                """
            )
            if cur.fetchone() is None:
                raise AssertionError("missing dm.students.grade_year")

            cur.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema='dm' AND table_name='syllabus_version_programs'
                """
            )
            if cur.fetchone() is None:
                raise AssertionError("missing dm.syllabus_version_programs")


if __name__ == "__main__":
    main()
