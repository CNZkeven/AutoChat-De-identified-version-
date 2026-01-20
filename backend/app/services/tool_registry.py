import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models import Tool
from .cache import TOOL_REGISTRY_CACHE_KEY, TOOL_REGISTRY_TTL, cache_get, cache_set

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

    def get_contract(self, name: str) -> dict[str, Any] | None:
        return self.tools.get(name)


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


def _ensure_list(value: Any) -> list[Any] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            logger.exception("Failed to parse tool safety filter")
            return None
    return None


def load_tool_registry(db: Session) -> ToolRegistry:
    cached = cache_get(TOOL_REGISTRY_CACHE_KEY)
    if isinstance(cached, dict) and cached:
        return ToolRegistry(cached)
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
            "output_schema": _ensure_dict(tool.output_schema),
            "auth_scope": tool.auth_scope,
            "rate_limit": tool.rate_limit,
            "safety_filter": _ensure_list(tool.safety_filter) or [],
        }
    if registry:
        cache_set(TOOL_REGISTRY_CACHE_KEY, registry, TOOL_REGISTRY_TTL)
    return ToolRegistry(registry)
