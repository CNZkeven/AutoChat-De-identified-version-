import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self, tools: dict[str, dict[str, Any]]) -> None:
        self.tools = tools

    def to_openai_tools(self) -> list[dict[str, Any]]:
        openai_tools = []
        for name, definition in self.tools.items():
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": definition.get("description", ""),
                        "parameters": definition.get("parameters", {}),
                    },
                }
            )
        return openai_tools

    def get_schema(self, name: str) -> dict[str, Any] | None:
        definition = self.tools.get(name)
        if not definition:
            return None
        return definition.get("parameters")


def _ensure_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            logger.exception("Failed to parse tool parameters schema")
            return None
    return None


def load_tool_registry(db: Session) -> ToolRegistry:
    tools = db.query(Tool).order_by(Tool.id.asc()).all()
    registry: dict[str, dict[str, Any]] = {}
    for tool in tools:
        schema = _ensure_dict(tool.parameters_schema)
        if not schema:
            logger.warning("Skipping tool %s due to invalid schema", tool.name)
            continue
        registry[tool.name] = {
            "description": tool.description,
            "parameters": schema,
        }
    return ToolRegistry(registry)
