"""Export and share API endpoints."""

import io
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Conversation, Message, ShareLink, User

router = APIRouter(prefix="/api/export", tags=["export"])

VALID_AGENTS = {"ideological", "evaluation", "task", "exploration", "competition", "course"}

AGENT_NAMES = {
    "ideological": "思政智能体",
    "evaluation": "评价智能体",
    "task": "任务智能体",
    "exploration": "探究智能体",
    "competition": "竞赛智能体",
    "course": "课程智能体",
}


class ShareLinkCreate(BaseModel):
    expires_days: int = 7


class ShareLinkResponse(BaseModel):
    share_url: str
    share_token: str
    expires_at: str | None


class SharedConversationResponse(BaseModel):
    title: str
    agent: str
    agent_name: str
    created_at: str
    messages: list[dict]


def _validate_agent(agent: str) -> str:
    """Validate agent type."""
    if agent not in VALID_AGENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent type. Must be one of: {', '.join(VALID_AGENTS)}",
        )
    return agent


def _get_user_conversation(
    db: Session, conversation_id: int, user_id: int, agent: str
) -> Conversation:
    """Get conversation and verify ownership."""
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.agent == agent,
        )
        .first()
    )

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    return conv


@router.get("/conversation/{conversation_id}/markdown")
def export_markdown(
    conversation_id: int = Path(..., description="Conversation ID"),
    agent: str = Query(..., description="Agent type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export conversation as Markdown file."""
    _validate_agent(agent)
    conv = _get_user_conversation(db, conversation_id, current_user.id, agent)

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    # Generate Markdown content
    agent_name = AGENT_NAMES.get(agent, agent)
    md_lines = [
        f"# {conv.title}",
        "",
        f"**智能体**: {agent_name}",
        f"**创建时间**: {conv.created_at.strftime('%Y-%m-%d %H:%M:%S') if conv.created_at else 'N/A'}",
        "",
        "---",
        "",
    ]

    for msg in messages:
        role_label = "**用户**" if msg.role == "user" else f"**{agent_name}**"
        timestamp = msg.created_at.strftime("%H:%M:%S") if msg.created_at else ""
        md_lines.append(f"{role_label} _{timestamp}_")
        md_lines.append("")
        md_lines.append(msg.content)
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    md_content = "\n".join(md_lines)

    # Sanitize filename
    safe_title = "".join(c for c in conv.title if c.isalnum() or c in " -_").strip()[:50]
    filename = f"{safe_title or 'conversation'}.md"

    return StreamingResponse(
        io.BytesIO(md_content.encode("utf-8")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/conversation/{conversation_id}/share", response_model=ShareLinkResponse)
def create_share_link(
    conversation_id: int = Path(..., description="Conversation ID"),
    agent: str = Query(..., description="Agent type"),
    payload: ShareLinkCreate = ShareLinkCreate(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareLinkResponse:
    """Create a shareable link for a conversation."""
    _validate_agent(agent)
    _get_user_conversation(db, conversation_id, current_user.id, agent)

    # Validate expires_days
    if payload.expires_days < 1 or payload.expires_days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expires_days must be between 1 and 30",
        )

    # Create share link
    share_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(datetime.UTC) + timedelta(days=payload.expires_days)

    share_link = ShareLink(
        conversation_id=conversation_id,
        share_token=share_token,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(share_link)
    db.commit()
    db.refresh(share_link)

    return ShareLinkResponse(
        share_url=f"/shared/{share_token}",
        share_token=share_token,
        expires_at=expires_at.isoformat(),
    )


@router.get("/shared/{token}", response_model=SharedConversationResponse)
def get_shared_conversation(
    token: str = Path(..., description="Share token"),
    db: Session = Depends(get_db),
) -> SharedConversationResponse:
    """Get a shared conversation (public endpoint - no auth required)."""
    share = (
        db.query(ShareLink)
        .filter(ShareLink.share_token == token, ShareLink.is_active == True)  # noqa: E712
        .first()
    )

    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found or inactive"
        )

    # Check expiration
    if share.expires_at and share.expires_at < datetime.now(datetime.UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Share link has expired"
        )

    # Increment view count
    share.view_count = (share.view_count or 0) + 1
    db.commit()

    # Get conversation
    conv = db.query(Conversation).filter(Conversation.id == share.conversation_id).first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    # Get messages
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == share.conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return SharedConversationResponse(
        title=conv.title,
        agent=conv.agent,
        agent_name=AGENT_NAMES.get(conv.agent, conv.agent),
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        messages=[
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in messages
        ],
    )


@router.delete("/share/{token}")
def revoke_share_link(
    token: str = Path(..., description="Share token"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Revoke a share link (only the conversation owner can do this)."""
    share = db.query(ShareLink).filter(ShareLink.share_token == token).first()

    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found"
        )

    # Verify ownership
    conv = db.query(Conversation).filter(Conversation.id == share.conversation_id).first()
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to revoke this share link",
        )

    share.is_active = False
    db.commit()

    return {"success": True, "message": "Share link revoked"}


@router.get("/conversation/{conversation_id}/shares")
def list_share_links(
    conversation_id: int = Path(..., description="Conversation ID"),
    agent: str = Query(..., description="Agent type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List all share links for a conversation."""
    _validate_agent(agent)
    _get_user_conversation(db, conversation_id, current_user.id, agent)

    shares = (
        db.query(ShareLink)
        .filter(ShareLink.conversation_id == conversation_id)
        .order_by(ShareLink.created_at.desc())
        .all()
    )

    return [
        {
            "token": s.share_token,
            "share_url": f"/shared/{s.share_token}",
            "is_active": s.is_active,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "view_count": s.view_count or 0,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in shares
    ]
