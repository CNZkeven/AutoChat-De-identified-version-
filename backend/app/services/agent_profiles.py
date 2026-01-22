from __future__ import annotations

from typing import Any

PROFILE_VERSION = "2026-01-19"

AGENT_PROFILES: dict[str, dict[str, Any]] = {
    "ideological": {
        "id": "ideological-v1",
        "version": PROFILE_VERSION,
        "title": "思政智能体",
        "allow_tools": {"get_user_comprehensive_profile", "search_knowledge_repository"},
        "scope": {"domain": "shipbuilding", "data": ["internal_kb"]},
        "template": "技术骨架/精神血肉/价值灵魂",
        "routing_hints": ["思政", "案例", "校史", "船魂精神"],
        "kpi": ["tool_accuracy", "groundedness", "latency", "cost"],
    },
    "evaluation": {
        "id": "evaluation-v1",
        "version": PROFILE_VERSION,
        "title": "评价智能体",
        "allow_tools": {
            "get_user_comprehensive_profile",
            "query_institutional_database",
            "execute_strategy_engine",
            "fetch_external_student_academic_data",
        },
        "scope": {"domain": "assessment", "data": ["internal_kb", "institution", "external_system"]},
        "template": "现状诊断/证据依据/改进建议/下一步",
        "routing_hints": ["评价", "达成", "指标", "改进"],
        "kpi": ["tool_accuracy", "groundedness", "latency", "cost"],
    },
    "task": {
        "id": "task-v1",
        "version": PROFILE_VERSION,
        "title": "任务智能体",
        "allow_tools": {
            "get_user_comprehensive_profile",
            "query_institutional_database",
            "execute_strategy_engine",
        },
        "scope": {"domain": "planning", "data": ["institution"]},
        "template": "任务拆解/优先级/时间规划/风险提醒",
        "routing_hints": ["任务", "计划", "提醒", "进度"],
        "kpi": ["tool_accuracy", "task_completion", "latency", "cost"],
    },
    "exploration": {
        "id": "exploration-v1",
        "version": PROFILE_VERSION,
        "title": "探究智能体",
        "allow_tools": {"search_knowledge_repository", "get_user_comprehensive_profile"},
        "scope": {"domain": "inquiry", "data": ["internal_kb"]},
        "template": "问题澄清/关键假设/引导问题/延伸阅读",
        "routing_hints": ["为什么", "如何证明", "深入分析", "反例"],
        "kpi": ["groundedness", "engagement", "latency", "cost"],
    },
    "competition": {
        "id": "competition-v1",
        "version": PROFILE_VERSION,
        "title": "竞赛智能体",
        "allow_tools": {
            "get_user_comprehensive_profile",
            "query_institutional_database",
            "search_knowledge_repository",
            "execute_strategy_engine",
        },
        "scope": {"domain": "contest", "data": ["internal_kb", "institution"]},
        "template": "赛事画像/能力差距/备赛路线/资源推荐",
        "routing_hints": ["竞赛", "比赛", "备赛", "获奖"],
        "kpi": ["tool_accuracy", "groundedness", "latency", "cost"],
    },
    "course": {
        "id": "course-v1",
        "version": PROFILE_VERSION,
        "title": "课程智能体",
        "allow_tools": {
            "get_user_comprehensive_profile",
            "query_institutional_database",
            "search_knowledge_repository",
        },
        "scope": {"domain": "course", "data": ["internal_kb", "institution"]},
        "template": "课程概览/学习路径/重点难点/练习建议",
        "routing_hints": ["课程", "选修", "推荐课", "难度"],
        "kpi": ["tool_accuracy", "groundedness", "latency", "cost"],
    },
}


def get_agent_profile(agent: str) -> dict[str, Any] | None:
    return AGENT_PROFILES.get(agent)


def get_agent_profile_version(agent: str) -> str | None:
    profile = get_agent_profile(agent)
    return profile.get("version") if profile else None


def get_agent_allowed_tools_from_profile(agent: str) -> set[str] | None:
    profile = get_agent_profile(agent)
    if not profile:
        return None
    allow_tools = profile.get("allow_tools")
    if isinstance(allow_tools, set):
        return allow_tools
    if isinstance(allow_tools, list):
        return set(allow_tools)
    return None
