import importlib.util
import json
import logging
import os
from collections.abc import Iterable

import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)

_PROXY_ENV_VARS = (
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
)


def _proxy_requires_socks() -> bool:
    for key in _PROXY_ENV_VARS:
        value = os.getenv(key)
        if value and value.lower().startswith("socks"):
            return True
    return False


def _socksio_available() -> bool:
    return importlib.util.find_spec("socksio") is not None


def _build_http_client() -> httpx.Client:
    trust_env = os.getenv("OPENAI_TRUST_ENV", "true").lower() not in {"0", "false", "no"}
    if not trust_env:
        return httpx.Client(trust_env=False)
    if _proxy_requires_socks() and not _socksio_available():
        logger.warning("SOCKS proxy detected but socksio is missing; ignoring proxy for AI requests.")
        return httpx.Client(trust_env=False)
    return httpx.Client(trust_env=True)


def call_ai_model_stream(
    model_name: str,
    messages: list[dict],
    api_key: str,
    base_url: str,
) -> Iterable[str]:
    if not api_key:
        raise RuntimeError("Agent API key is not configured")
    if not base_url:
        raise RuntimeError("Agent base URL is not configured")

    client = OpenAI(api_key=api_key, base_url=base_url, http_client=_build_http_client())
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=True,
        max_tokens=4096,
        temperature=0.7,
    )
    for chunk in response:
        try:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
        except Exception:
            logger.exception("Failed to parse streaming chunk: %s", json.dumps(chunk.model_dump()))
