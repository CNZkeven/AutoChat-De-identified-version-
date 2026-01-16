import json
import logging
from collections.abc import Iterable

from openai import OpenAI

logger = logging.getLogger(__name__)


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

    client = OpenAI(api_key=api_key, base_url=base_url)
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
