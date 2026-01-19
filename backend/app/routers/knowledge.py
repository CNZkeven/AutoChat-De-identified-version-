from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Knowledge, User
from ..schemas import (
    KnowledgeContextResponse,
    KnowledgeCreate,
    KnowledgeOut,
    KnowledgeSearchRequest,
    KnowledgeUpdate,
)
from ..services.knowledge import (
    create_knowledge,
    delete_knowledge,
    get_knowledge,
    list_knowledge,
    search_knowledge,
    update_knowledge,
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeOut])
def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return list_knowledge(db, skip=skip, limit=limit)


@router.post("", response_model=KnowledgeOut, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    knowledge = Knowledge(**payload.model_dump())
    return update_knowledge(db, knowledge)


@router.get("/{knowledge_id}", response_model=KnowledgeOut)
def get_item(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    knowledge = get_knowledge(db, knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge not found")
    return knowledge


@router.patch("/{knowledge_id}", response_model=KnowledgeOut)
def update_item(
    knowledge_id: int,
    payload: KnowledgeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    knowledge = get_knowledge(db, knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(knowledge, key, value)
    return create_knowledge(db, knowledge)


@router.delete("/{knowledge_id}")
def delete_item(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    knowledge = get_knowledge(db, knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge not found")
    delete_knowledge(db, knowledge)
    return {"success": True}


@router.post("/search", response_model=list[KnowledgeOut])
def search_items(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return search_knowledge(db, payload.query, limit=payload.limit)


@router.post("/context", response_model=KnowledgeContextResponse)
def get_context(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    items = search_knowledge(db, payload.query, limit=payload.limit)
    context = "\n\n".join([f"{item.title}\n{item.content}" for item in items])
    return KnowledgeContextResponse(context=context, total=len(items))
