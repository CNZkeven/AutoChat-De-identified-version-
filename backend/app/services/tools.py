from sqlalchemy.orm import Session

from ..models import Tool


def list_tools(db: Session, skip: int = 0, limit: int = 100) -> list[Tool]:
    return db.query(Tool).order_by(Tool.id.asc()).offset(skip).limit(limit).all()


def get_tool_by_name(db: Session, name: str) -> Tool | None:
    return db.query(Tool).filter(Tool.name == name).first()


def create_tool(db: Session, tool: Tool) -> Tool:
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


def update_tool(db: Session, tool: Tool) -> Tool:
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


def delete_tool(db: Session, tool: Tool) -> None:
    db.delete(tool)
    db.commit()
