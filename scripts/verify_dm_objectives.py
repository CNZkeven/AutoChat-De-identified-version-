import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.academics import list_course_objectives


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
    offering_id = 3

    with SessionLocal() as db:
        objectives = list_course_objectives(db, student_no, offering_id)

    indices = [obj.get("objective_index") for obj in objectives if obj.get("objective_index")]
    if len(indices) != len(set(indices)):
        raise AssertionError("duplicate objective_index detected")


if __name__ == "__main__":
    main()
