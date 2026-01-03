"""Memory summarization service for per-agent long-term memory."""

import logging

from openai import OpenAI
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import OPENAI_API_KEY, OPENAI_BASE_URL
from ..models import Conversation, MemorySummary, Message

logger = logging.getLogger(__name__)

# Configuration
SUMMARIZATION_THRESHOLD = 20  # Trigger summarization after 20 new messages
SUMMARIZATION_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # Use base model for summarization
MAX_MESSAGES_FOR_SUMMARY = 100  # Maximum messages to include in summarization

SUMMARIZATION_PROMPT = """你是一个对话记忆助手。请分析以下用户与AI智能体的对话历史，并创建一份简洁的记忆摘要。

摘要应包含：
1. 用户讨论的主要话题和关注点
2. 用户表达的偏好、兴趣或习惯
3. 任何重要的背景信息或上下文
4. 用户提到的目标或任务

请用200-300字创建摘要，使用第三人称描述用户（如"该用户..."）。

对话历史：
{conversation_history}

记忆摘要："""


def get_agent_memory(db: Session, user_id: int, agent: str) -> MemorySummary | None:
    """Fetch memory summary for specific user-agent pair."""
    return (
        db.query(MemorySummary)
        .filter(MemorySummary.user_id == user_id, MemorySummary.agent == agent)
        .first()
    )


def fetch_latest_memory_summary(db: Session, user_id: int, agent: str | None = None) -> str | None:
    """Fetch the latest memory summary text for a user (optionally filtered by agent).

    This is the main function called by chat router.
    """
    query = db.query(MemorySummary).filter(MemorySummary.user_id == user_id)

    if agent:
        query = query.filter(MemorySummary.agent == agent)

    summary = query.order_by(MemorySummary.updated_at.desc()).first()

    if summary:
        return summary.summary
    return None


def count_user_agent_messages(db: Session, user_id: int, agent: str) -> int:
    """Count total messages for a user-agent combination."""
    return (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id, Conversation.agent == agent)
        .scalar()
        or 0
    )


def _call_summarization_api(conversation_text: str) -> str | None:
    """Call LLM to generate memory summary."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured, skipping summarization")
        return None

    try:
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        prompt = SUMMARIZATION_PROMPT.format(conversation_history=conversation_text)

        response = client.chat.completions.create(
            model=SUMMARIZATION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.3,  # Lower temperature for more consistent summaries
        )

        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()

    except Exception:
        logger.exception("Failed to generate memory summary")

    return None


def generate_memory_summary(
    db: Session, user_id: int, agent: str, force: bool = False
) -> MemorySummary | None:
    """Generate or update memory summary when message threshold is reached.

    Args:
        db: Database session
        user_id: User ID
        agent: Agent type
        force: If True, regenerate even if threshold not reached

    Returns:
        Updated or created MemorySummary, or None if not needed/failed
    """
    # Count current messages
    message_count = count_user_agent_messages(db, user_id, agent)

    # Get existing summary
    existing = get_agent_memory(db, user_id, agent)
    last_summarized_count = existing.message_count if existing else 0

    # Check if we need to summarize
    new_messages = message_count - last_summarized_count
    if not force and new_messages < SUMMARIZATION_THRESHOLD:
        logger.debug(
            "Skipping summarization: %d new messages (threshold: %d)",
            new_messages,
            SUMMARIZATION_THRESHOLD,
        )
        return existing

    logger.info(
        "Generating memory summary for user=%d agent=%s (messages: %d, new: %d)",
        user_id,
        agent,
        message_count,
        new_messages,
    )

    # Fetch recent conversations for summarization
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id, Conversation.agent == agent)
        .order_by(Conversation.updated_at.desc())
        .limit(10)  # Last 10 conversations
        .all()
    )

    if not conversations:
        logger.debug("No conversations found for summarization")
        return existing

    # Build conversation history text
    history_parts = []
    total_messages = 0

    for conv in reversed(conversations):  # Oldest first
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .all()
        )

        for msg in messages:
            if total_messages >= MAX_MESSAGES_FOR_SUMMARY:
                break
            role = "用户" if msg.role == "user" else "AI"
            # Truncate long messages
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            history_parts.append(f"{role}: {content}")
            total_messages += 1

        if total_messages >= MAX_MESSAGES_FOR_SUMMARY:
            break

    if not history_parts:
        logger.debug("No messages found for summarization")
        return existing

    conversation_text = "\n\n".join(history_parts)

    # Call LLM to generate summary
    summary_text = _call_summarization_api(conversation_text)

    if not summary_text:
        logger.warning("Failed to generate summary text")
        return existing

    # Upsert memory summary
    conversation_ids = [c.id for c in conversations]

    if existing:
        existing.summary = summary_text
        existing.message_count = message_count
        existing.conversation_ids = conversation_ids
        db.commit()
        db.refresh(existing)
        logger.info("Updated memory summary id=%d", existing.id)
        return existing
    else:
        new_summary = MemorySummary(
            user_id=user_id,
            agent=agent,
            summary=summary_text,
            message_count=message_count,
            conversation_ids=conversation_ids,
        )
        db.add(new_summary)
        db.commit()
        db.refresh(new_summary)
        logger.info("Created memory summary id=%d", new_summary.id)
        return new_summary


def clear_agent_memory(db: Session, user_id: int, agent: str) -> bool:
    """Clear memory for a specific agent."""
    memory = get_agent_memory(db, user_id, agent)
    if memory:
        db.delete(memory)
        db.commit()
        logger.info("Cleared memory for user=%d agent=%s", user_id, agent)
        return True
    return False
