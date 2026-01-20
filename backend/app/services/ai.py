import importlib.util
import json
import logging
import os
from collections.abc import Iterable
from typing import Any

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


def call_ai_model_with_tools(
    model_name: str,
    messages: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    tools: list[dict[str, Any]],
    tool_choice: str = "auto",
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    if not api_key:
        raise RuntimeError("Agent API key is not configured")
    if not base_url:
        raise RuntimeError("Agent base URL is not configured")

    client = OpenAI(api_key=api_key, base_url=base_url, http_client=_build_http_client())
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        max_tokens=2048,
        temperature=0.7,
    )
    message = response.choices[0].message
    content = message.content or ""
    raw_tool_calls: list[dict[str, Any]] = []
    parsed_tool_calls: list[dict[str, Any]] = []

    for call in message.tool_calls or []:
        try:
            raw_tool_calls.append(call.model_dump())
        except Exception:
            logger.exception("Failed to serialize tool call")
            continue
        name = getattr(call.function, "name", None)
        raw_args = getattr(call.function, "arguments", None) or "{}"
        try:
            parsed_args = json.loads(raw_args)
            if not isinstance(parsed_args, dict):
                parsed_args = {"_raw": raw_args}
        except Exception:
            parsed_args = {"_raw": raw_args}
        parsed_tool_calls.append(
            {
                "id": call.id,
                "name": name,
                "args": parsed_args,
            }
        )

    # Fallback: 일부供应商将工具调用写入 reasoning_content
    if not parsed_tool_calls:
        try:
            dumped = message.model_dump()
        except Exception:
            dumped = {}
        reasoning = dumped.get("reasoning_content")
        if reasoning:
            raw_tool_calls.append({"reasoning_content": reasoning})
            parsed_tool_calls.extend(_parse_reasoning_tool_calls(reasoning))

    return content, parsed_tool_calls, raw_tool_calls


def call_ai_model(
    model_name: str,
    messages: list[dict[str, Any]],
    api_key: str,
    base_url: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    if not api_key:
        raise RuntimeError("Agent API key is not configured")
    if not base_url:
        raise RuntimeError("Agent base URL is not configured")

    client = OpenAI(api_key=api_key, base_url=base_url, http_client=_build_http_client())
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    message = response.choices[0].message
    return (message.content or "").strip()


def _parse_reasoning_tool_calls(reasoning: str) -> list[dict[str, Any]]:
    if not reasoning:
        return []
    calls: list[dict[str, Any]] = []
    start = 0
    while True:
        open_tag = reasoning.find("<tool_call>", start)
        if open_tag == -1:
            break
        close_tag = reasoning.find("</tool_call>", open_tag)
        if close_tag == -1:
            break
        payload = reasoning[open_tag + len("<tool_call>") : close_tag].strip()
        start = close_tag + len("</tool_call>")
        if not payload:
            continue
        try:
            data = json.loads(payload)
        except Exception:
            continue
        if isinstance(data, dict) and "name" in data:
            args = data.get("arguments", {})
            calls.append(
                {
                    "id": None,
                    "name": data.get("name"),
                    "args": args if isinstance(args, dict) else {"_raw": args},
                }
            )
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item:
                    args = item.get("arguments", {})
                    calls.append(
                        {
                            "id": None,
                            "name": item.get("name"),
                            "args": args if isinstance(args, dict) else {"_raw": args},
                        }
                    )
    return calls
