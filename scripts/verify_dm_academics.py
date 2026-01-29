import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.services.academics import list_student_courses


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql://", 1)
    return url


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    engine = create_engine(_normalize_url(database_url))
    SessionLocal = sessionmaker(bind=engine)

    student_no = "232241816204"
    with SessionLocal() as db:
        in_class_rows = db.execute(
            text(
                """
                SELECT o.offering_id
                  FROM dm.enrollments e
                  JOIN dm.course_offerings o ON o.offering_id = e.offering_id
                 WHERE e.student_no = :student_no
                   AND COALESCE(o.is_in_class_experiment, false) = true
                """
            ),
            {"student_no": student_no},
        ).fetchall()
        in_class_ids = {row[0] for row in in_class_rows}

        courses = list_student_courses(db, student_no)
        offering_ids = {course.get("offering_id") for course in courses}

        if in_class_ids.intersection(offering_ids):
            raise AssertionError("in-class experiment offerings were not filtered")

        if not any(course.get("class_number") for course in courses):
            raise AssertionError("class_number missing in academic list")


if __name__ == "__main__":
    main()
