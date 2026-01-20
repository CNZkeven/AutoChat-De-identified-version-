#!/usr/bin/env python3
"""Fetch SiliconFlow models and write a report to docs.

Usage:
  SILICONFLOW_API_KEY=... SILICONFLOW_BASE_URL=... python3 scripts/fetch_siliconflow_models.py

If env vars are not set, the script will attempt to read them from backend/.env.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
import urllib.request

try:
    import certifi
except Exception:  # pragma: no cover - optional
    certifi = None


ENV_FILE_CANDIDATES = [Path("backend/.env"), Path(".env")]


def load_env_file() -> dict[str, str]:
    data: dict[str, str] = {}
    for path in ENV_FILE_CANDIDATES:
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            data[key] = value
    return data


def resolve_config() -> tuple[str, str, str]:
    """Return api_key, base_url, source_note."""
    source_note = "env"
    api_key = os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("SILICONFLOW_BASE_URL")

    if api_key and base_url:
        return api_key, base_url, source_note

    env_file = load_env_file()
    api_key = api_key or env_file.get("SILICONFLOW_API_KEY")
    base_url = base_url or env_file.get("SILICONFLOW_BASE_URL")

    if api_key and base_url:
        return api_key, base_url, "env-file"

    # No fallback to other keys to avoid surprising behavior.
    missing = []
    if not api_key:
        missing.append("SILICONFLOW_API_KEY")
    if not base_url:
        missing.append("SILICONFLOW_BASE_URL")
    raise SystemExit(f"Missing required env vars: {', '.join(missing)}")


def build_models_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/models"
    return f"{base}/v1/models"


def fetch_models(url: str, api_key: str) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {api_key}"}
    request = urllib.request.Request(url, headers=headers)

    context = None
    if certifi is not None:
        context = ssl.create_default_context(cafile=certifi.where())

    if os.getenv("SILICONFLOW_TLS_SKIP_VERIFY") == "1":
        context = ssl._create_unverified_context()  # noqa: SLF001

    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    return []


def normalize_modalities(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).lower() for v in value]
    if isinstance(value, dict):
        return [str(k).lower() for k, enabled in value.items() if enabled]
    return [str(value).lower()]


def infer_capabilities(model: dict[str, Any]) -> str:
    model_id = str(model.get("id") or model.get("name") or "").lower()
    caps = set()

    for modality in normalize_modalities(model.get("modalities")):
        if "image" in modality or "vision" in modality:
            caps.add("图形")
        if "audio" in modality or "speech" in modality or "voice" in modality:
            caps.add("音频")
        if "embed" in modality:
            caps.add("嵌入")
        if "text" in modality or "chat" in modality:
            caps.add("对话")

    for key, label in [
        ("capabilities", None),
        ("capability", None),
    ]:
        value = model.get(key)
        if isinstance(value, dict):
            for cap_key, enabled in value.items():
                if not enabled:
                    continue
                cap_key = str(cap_key).lower()
                if "image" in cap_key or "vision" in cap_key:
                    caps.add("图形")
                if "audio" in cap_key or "speech" in cap_key:
                    caps.add("音频")
                if "embed" in cap_key:
                    caps.add("嵌入")
                if "chat" in cap_key or "text" in cap_key:
                    caps.add("对话")

    if any(token in model_id for token in ["embed", "embedding", "rerank", "reranker", "bge-", "gte-", "e5"]):
        caps.add("嵌入")
    if any(token in model_id for token in ["vision", "vl", "multimodal", "mm", "image", "omni"]):
        caps.add("图形")
    if any(token in model_id for token in ["audio", "speech", "voice", "tts", "asr"]):
        caps.add("音频")

    if not caps and any(token in model_id for token in ["chat", "instruct", "assistant", "think"]):
        caps.add("对话")
    if not caps:
        caps.add("未知")

    return "、".join(sorted(caps))


def extract_context_length(model: dict[str, Any]) -> str:
    candidates = [
        "context_length",
        "max_context_length",
        "max_tokens",
        "max_total_tokens",
        "max_input_tokens",
        "max_output_tokens",
        "context",
    ]
    for key in candidates:
        if key in model and model[key] is not None:
            return str(model[key])
    return "未提供"


def extract_pricing(model: dict[str, Any]) -> tuple[str, str]:
    pricing = None
    for key in ["pricing", "price", "prices", "cost", "billing"]:
        if key in model and model[key] is not None:
            pricing = model[key]
            break

    if pricing is None:
        return "未提供", "未提供"

    if isinstance(pricing, dict):
        input_price = None
        output_price = None
        unit = None
        for key, value in pricing.items():
            k = str(key).lower()
            if "input" in k or "prompt" in k:
                input_price = value
            if "output" in k or "completion" in k:
                output_price = value
            if "unit" in k or "currency" in k:
                unit = value
        price_parts = []
        if input_price is not None:
            price_parts.append(f"input={input_price}")
        if output_price is not None:
            price_parts.append(f"output={output_price}")
        if unit is not None:
            price_parts.append(f"unit={unit}")
        price_text = ", ".join(price_parts) if price_parts else json.dumps(pricing, ensure_ascii=False)
        cost_text = price_text
        return price_text, cost_text

    return str(pricing), str(pricing)


def render_markdown(
    models: list[dict[str, Any]],
    base_url: str,
    source_note: str,
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# SiliconFlow 模型清单",
        "",
        f"- 生成时间: {generated_at}",
        f"- API Base: {base_url}",
        f"- 数据来源: GET /v1/models ({source_note})",
        "- 说明: /v1/models 当前未返回价格/上下文长度/能力等字段，若缺失则标记为“未提供”。能力为字段或模型名推断，可能不完全准确。",
        "",
        "| 模型ID | 上下文长度 | 能力 | 价格 | 成本 | 备注 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for model in models:
        model_id = model.get("id") or model.get("name") or "unknown"
        context_len = extract_context_length(model)
        capabilities = infer_capabilities(model)
        price, cost = extract_pricing(model)
        note = "未提供" if price == "未提供" else ""
        lines.append(
            f"| {model_id} | {context_len} | {capabilities} | {price} | {cost} | {note} |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    api_key, base_url, source_note = resolve_config()
    url = build_models_url(base_url)
    models = fetch_models(url, api_key)
    if not models:
        raise SystemExit("No models returned from API")

    output = render_markdown(models, base_url, source_note)
    output_path = Path("docs/SiliconFlowModels.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")

    print(f"Wrote {len(models)} models to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
