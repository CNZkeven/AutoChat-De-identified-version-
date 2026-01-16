import logging

from openai import OpenAI
from sqlalchemy.orm import Session

from ..config import SUMMARY_API_KEY, SUMMARY_BASE_URL, SUMMARY_MODEL
from ..models import Conversation, Message

logger = logging.getLogger(__name__)

MAX_MESSAGES_FOR_TITLE = 12

TITLE_PROMPT = """你是一个对话标题生成助手。请根据以下对话内容生成一个简洁的中文标题。

要求：
1. 仅输出标题，不要额外解释。
2. 控制在12个汉字以内，避免使用引号或多余标点。
3. 标题应准确反映对话主题。

对话内容：
{conversation}

标题："""


def _build_conversation_excerpt(messages: list[Message]) -> str:
    lines = []
    for msg in messages:
        role = "用户" if msg.role == "user" else "智能体"
        content = msg.content.strip()
        if not content:
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def generate_conversation_title(db: Session, conversation_id: int) -> str | None:
    if not SUMMARY_API_KEY or not SUMMARY_BASE_URL or not SUMMARY_MODEL:
        logger.info("Summary API not configured, skipping title generation")
        return None

    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not convo:
        return None

    if convo.title and convo.title.strip() not in {"新对话", "New conversation"}:
        return None

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(MAX_MESSAGES_FOR_TITLE)
        .all()
    )

    if not messages:
        return None

    excerpt = _build_conversation_excerpt(messages)
    if not excerpt:
        return None

    try:
        client = OpenAI(api_key=SUMMARY_API_KEY, base_url=SUMMARY_BASE_URL)
        prompt = TITLE_PROMPT.format(conversation=excerpt)
        response = client.chat.completions.create(
            model=SUMMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=64,
            temperature=0.3,
        )

        if not response.choices or not response.choices[0].message.content:
            return None

        title = response.choices[0].message.content.strip().strip('"').strip("'")
        if not title:
            return None

        title = title.splitlines()[0].strip()
        if len(title) > 20:
            title = title[:20].rstrip()

        convo.title = title
        db.commit()
        return title
    except Exception:
        logger.exception("Failed to generate conversation title")
        return None
