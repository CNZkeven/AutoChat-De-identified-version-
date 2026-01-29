import os

import psycopg


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    with psycopg.connect(_normalize_url(database_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT offering_id, selected_syllabus_version_id, is_in_class_experiment
                  FROM dm.course_offerings
                 WHERE offering_id IN (3, 523)
                 ORDER BY offering_id
                """
            )
            rows = cur.fetchall()
            if not rows:
                raise AssertionError("missing dm.course_offerings rows for validation")
            if rows[0][1] is None:
                raise AssertionError("missing selected_syllabus_version_id")
            if rows[1][2] is None:
                raise AssertionError("missing is_in_class_experiment")


if __name__ == "__main__":
    main()
