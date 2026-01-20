from __future__ import annotations

import json
import logging
from typing import Any

from ..config import SUMMARY_API_KEY, SUMMARY_BASE_URL, SUMMARY_MODEL
from .ai import call_ai_model

logger = logging.getLogger(__name__)

RULES = [
    ("task", ["待办", "截止", "任务", "提醒", "进度", "计划"]),
    ("course", ["课程", "选修", "推荐课", "难度", "学分", "教学"]),
    ("evaluation", ["评价", "达成", "指标点", "毕业要求", "改进"]),
    ("competition", ["竞赛", "比赛", "备赛", "获奖", "队伍", "指导"]),
    ("ideological", ["思政", "案例", "校史", "船魂", "大国智造"]),
    ("exploration", ["为什么", "如何证明", "深入分析", "反例", "你怎么看"]),
]


def route_by_rules(text: str) -> tuple[str | None, list[str]]:
    hits: list[str] = []
    for agent, keywords in RULES:
        if any(keyword in text for keyword in keywords):
            hits.append(agent)
    if hits:
        return hits[0], hits
    return None, []


def _parse_router_json(content: str) -> dict[str, Any] | None:
    if not content:
        return None
    trimmed = content.strip()
    if trimmed.startswith("{"):
        try:
            return json.loads(trimmed)
        except Exception:
            return None
    if "```" in content:
        parts = content.split("```")
        if len(parts) >= 3:
            candidate = parts[1]
            if "\n" in candidate:
                candidate = candidate.split("\n", 1)[1]
            try:
                return json.loads(candidate.strip())
            except Exception:
                return None
    return None


def route_by_llm(text: str, candidates: list[str]) -> dict[str, Any] | None:
    if not SUMMARY_API_KEY or not SUMMARY_BASE_URL or not SUMMARY_MODEL:
        return None
    prompt = (
        "你是路由器，请根据用户输入选择最合适的智能体，并输出JSON。"
        "\n候选智能体：" + ", ".join(candidates)
        + "\n输出JSON格式：{\"agent_id\":\"...\",\"reason\":\"...\",\"missing_slots\":[]}"
        + "\n用户输入：" + text
    )
    try:
        content = call_ai_model(
            SUMMARY_MODEL,
            [{"role": "user", "content": prompt}],
            api_key=SUMMARY_API_KEY,
            base_url=SUMMARY_BASE_URL,
        )
        return _parse_router_json(content)
    except Exception:
        logger.exception("LLM routing failed")
        return None


def resolve_agent(text: str, candidates: list[str], default_agent: str) -> dict[str, Any]:
    agent_id, hits = route_by_rules(text)
    if agent_id:
        return {"agent_id": agent_id, "method": "rule", "hits": hits, "missing_slots": []}

    llm_decision = route_by_llm(text, candidates)
    if llm_decision and llm_decision.get("agent_id") in candidates:
        return {
            "agent_id": llm_decision.get("agent_id"),
            "method": "llm",
            "hits": [],
            "missing_slots": llm_decision.get("missing_slots") or [],
            "reason": llm_decision.get("reason"),
        }

    return {"agent_id": default_agent, "method": "default", "hits": [], "missing_slots": []}
