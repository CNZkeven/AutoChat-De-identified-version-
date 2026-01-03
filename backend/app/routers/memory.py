"""Memory management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..services.memory import (
    clear_agent_memory,
    count_user_agent_messages,
    generate_memory_summary,
    get_agent_memory,
)

router = APIRouter(prefix="/api/memory", tags=["memory"])

VALID_AGENTS = {"ideological", "evaluation", "task", "exploration", "competition", "course"}


class MemoryResponse(BaseModel):
    summary: str | None
    message_count: int
    updated_at: str | None


class MemoryActionResponse(BaseModel):
    success: bool
    summary: str | None = None
    message: str | None = None


def _validate_agent(agent: str) -> str:
    """Validate agent type."""
    if agent not in VALID_AGENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent type. Must be one of: {', '.join(VALID_AGENTS)}",
        )
    return agent


@router.get("/{agent}", response_model=MemoryResponse)
def get_memory(
    agent: str = Path(..., description="Agent type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemoryResponse:
    """Get memory summary for a specific agent."""
    _validate_agent(agent)

    memory = get_agent_memory(db, current_user.id, agent)

    if not memory:
        # Return message count even if no memory exists
        message_count = count_user_agent_messages(db, current_user.id, agent)
        return MemoryResponse(summary=None, message_count=message_count, updated_at=None)

    return MemoryResponse(
        summary=memory.summary,
        message_count=memory.message_count,
        updated_at=memory.updated_at.isoformat() if memory.updated_at else None,
    )


@router.post("/{agent}/regenerate", response_model=MemoryActionResponse)
def regenerate_memory(
    agent: str = Path(..., description="Agent type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemoryActionResponse:
    """Force regenerate memory summary for a specific agent."""
    _validate_agent(agent)

    memory = generate_memory_summary(db, current_user.id, agent, force=True)

    if memory:
        return MemoryActionResponse(
            success=True, summary=memory.summary, message="Memory regenerated successfully"
        )

    return MemoryActionResponse(
        success=False, summary=None, message="Failed to regenerate memory. No conversations found."
    )


@router.delete("/{agent}", response_model=MemoryActionResponse)
def delete_memory(
    agent: str = Path(..., description="Agent type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemoryActionResponse:
    """Clear memory for a specific agent."""
    _validate_agent(agent)

    success = clear_agent_memory(db, current_user.id, agent)

    if success:
        return MemoryActionResponse(success=True, message="Memory cleared successfully")

    return MemoryActionResponse(success=False, message="No memory found for this agent")


@router.get("", response_model=dict)
def list_all_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List memory summaries for all agents."""
    result = {}

    for agent in VALID_AGENTS:
        memory = get_agent_memory(db, current_user.id, agent)
        message_count = count_user_agent_messages(db, current_user.id, agent)

        result[agent] = {
            "has_memory": memory is not None,
            "summary_preview": memory.summary[:100] + "..." if memory and len(memory.summary) > 100 else (memory.summary if memory else None),
            "message_count": message_count,
            "updated_at": memory.updated_at.isoformat() if memory and memory.updated_at else None,
        }

    return result
