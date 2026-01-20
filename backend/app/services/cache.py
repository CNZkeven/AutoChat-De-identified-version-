from __future__ import annotations

import hashlib
import json
import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

try:  # optional dependency
    import redis
except Exception:  # pragma: no cover
    redis = None

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

TOOL_REGISTRY_CACHE_KEY = "tool_registry:v1"
TOOL_REGISTRY_TTL = int(os.getenv("CACHE_TOOL_REGISTRY_TTL", "3600"))
PROFILE_CACHE_TTL = int(os.getenv("CACHE_PROFILE_TTL", "60"))
INSTITUTION_CACHE_TTL = int(os.getenv("CACHE_INSTITUTION_TTL", "300"))
KNOWLEDGE_CACHE_TTL = int(os.getenv("CACHE_KNOWLEDGE_TTL", "300"))


def make_cache_key(prefix: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


@lru_cache(maxsize=1)
def _get_client():
    if redis is None:
        logger.info("Redis client not available; caching disabled")
        return None
    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception:
        logger.exception("Failed to connect to Redis; caching disabled")
        return None


def cache_get(key: str) -> Any | None:
    client = _get_client()
    if not client:
        return None
    try:
        value = client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception:
        logger.exception("Redis get failed for key=%s", key)
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> bool:
    client = _get_client()
    if not client:
        return False
    try:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        if ttl:
            client.setex(key, ttl, payload)
        else:
            client.set(key, payload)
        return True
    except Exception:
        logger.exception("Redis set failed for key=%s", key)
        return False


def cache_health() -> dict[str, Any]:
    client = _get_client()
    if not client:
        return {"ok": False, "reason": "redis_unavailable"}
    try:
        pong = client.ping()
        return {"ok": True, "pong": pong}
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}
