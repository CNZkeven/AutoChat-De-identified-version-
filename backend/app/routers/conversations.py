from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Conversation, Message, User
from ..schemas import ConversationCreate, ConversationOut, ConversationUpdate, MessageOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _get_conversation(
    db: Session, conversation_id: int, user_id: int, agent: str
) -> Conversation:
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.agent == agent,
        )
        .first()
    )
    if not convo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return convo


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    agent: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id, Conversation.agent == agent)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return rows


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    agent: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = (payload.title or "新对话").strip() or "新对话"
    convo = Conversation(
        user_id=current_user.id,
        title=title,
        agent=agent,
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.patch("/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    agent: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = _get_conversation(db, conversation_id, current_user.id, agent)
    convo.title = payload.title.strip() or "新对话"
    convo.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(convo)
    return convo


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    agent: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    convo = _get_conversation(db, conversation_id, current_user.id, agent)
    db.delete(convo)
    db.commit()
    return {"success": True}


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: int,
    agent: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_conversation(db, conversation_id, current_user.id, agent)
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
        .all()
    )
    return rows
