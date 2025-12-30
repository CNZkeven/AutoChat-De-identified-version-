from typing import Optional

from sqlalchemy.orm import Session

from ..models import MemorySummary


def fetch_latest_memory_summary(db: Session, user_id: int) -> Optional[str]:
    summary = (
        db.query(MemorySummary)
        .filter(MemorySummary.user_id == user_id)
        .order_by(MemorySummary.updated_at.desc())
        .first()
    )
    if summary:
        return summary.summary
    return None
