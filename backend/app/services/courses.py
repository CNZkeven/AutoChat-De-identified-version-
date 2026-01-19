from sqlalchemy.orm import Session

from ..models import Course


def list_courses(db: Session, skip: int = 0, limit: int = 50) -> list[Course]:
    return db.query(Course).order_by(Course.id.desc()).offset(skip).limit(limit).all()


def get_course(db: Session, course_id: int) -> Course | None:
    return db.query(Course).filter(Course.id == course_id).first()


def create_course(db: Session, course: Course) -> Course:
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course: Course) -> Course:
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def delete_course(db: Session, course: Course) -> None:
    db.delete(course)
    db.commit()
