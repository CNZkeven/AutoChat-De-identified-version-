from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Knowledge


def list_knowledge(db: Session, skip: int = 0, limit: int = 50) -> list[Knowledge]:
    return db.query(Knowledge).order_by(Knowledge.id.desc()).offset(skip).limit(limit).all()


def get_knowledge(db: Session, knowledge_id: int) -> Knowledge | None:
    return db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()


def create_knowledge(db: Session, knowledge: Knowledge) -> Knowledge:
    db.add(knowledge)
    db.commit()
    db.refresh(knowledge)
    return knowledge


def update_knowledge(db: Session, knowledge: Knowledge) -> Knowledge:
    db.add(knowledge)
    db.commit()
    db.refresh(knowledge)
    return knowledge


def delete_knowledge(db: Session, knowledge: Knowledge) -> None:
    db.delete(knowledge)
    db.commit()


def search_knowledge(db: Session, query: str, limit: int = 5) -> list[Knowledge]:
    pattern = f"%{query}%"
    return (
        db.query(Knowledge)
        .filter(or_(Knowledge.title.ilike(pattern), Knowledge.content.ilike(pattern)))
        .order_by(Knowledge.id.desc())
        .limit(limit)
        .all()
    )
