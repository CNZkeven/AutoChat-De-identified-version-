from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import KnowledgeContextResponse, KnowledgeSearchRequest
from ..services.knowledge import search_knowledge

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/search", response_model=list[KnowledgeContextResponse])
def search(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    items = search_knowledge(db, payload.query, limit=payload.limit)
    return [
        KnowledgeContextResponse(context=f"{item.title}\n{item.content}", total=1)
        for item in items
    ]


@router.post("/context", response_model=KnowledgeContextResponse)
def context(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    items = search_knowledge(db, payload.query, limit=payload.limit)
    context = "\n\n".join([f"{item.title}\n{item.content}" for item in items])
    return KnowledgeContextResponse(context=context, total=len(items))
