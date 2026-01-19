from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Tool, User
from ..schemas import ToolCreate, ToolOut, ToolUpdate
from ..services.tools import create_tool, delete_tool, get_tool_by_name, list_tools, update_tool

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=list[ToolOut])
def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return list_tools(db, skip=skip, limit=limit)


@router.post("", response_model=ToolOut, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ToolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    existing = get_tool_by_name(db, payload.name)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tool already exists")
    tool = Tool(**payload.model_dump())
    return update_tool(db, tool)


@router.patch("/{name}", response_model=ToolOut)
def update_item(
    name: str,
    payload: ToolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    tool = get_tool_by_name(db, name)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tool, key, value)
    return create_tool(db, tool)


@router.delete("/{name}")
def delete_item(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    tool = get_tool_by_name(db, name)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    delete_tool(db, tool)
    return {"success": True}
