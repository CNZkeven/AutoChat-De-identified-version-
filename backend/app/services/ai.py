import json
import logging
from typing import Iterable, List

from openai import OpenAI

from ..config import OPENAI_API_KEY, OPENAI_BASE_URL

logger = logging.getLogger(__name__)


def call_ai_model_stream(model_name: str, messages: List[dict]) -> Iterable[str]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
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
