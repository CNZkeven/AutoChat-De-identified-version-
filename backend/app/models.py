from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from .db import Base

course_prerequisite_association = Table(
    "course_prerequisite_association",
    Base.metadata,
    Column("from_course_id", Integer, ForeignKey("courses.id", ondelete="CASCADE")),
    Column("to_course_id", Integer, ForeignKey("courses.id", ondelete="CASCADE")),
)

course_related_association = Table(
    "course_related_association",
    Base.metadata,
    Column("course_id_1", Integer, ForeignKey("courses.id", ondelete="CASCADE")),
    Column("course_id_2", Integer, ForeignKey("courses.id", ondelete="CASCADE")),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    agent = Column(String(40), nullable=False, index=True)
    status = Column(String(40), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MemorySummary(Base):
    __tablename__ = "memory_summaries"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent = Column(String(40), nullable=False, index=True)  # Per-agent memory
    summary = Column(Text, nullable=False)
    message_count = Column(Integer, default=0)  # Track message count at summarization
    conversation_ids = Column(JSONB, default=list)  # Track summarized conversations
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_memory_user_agent", "user_id", "agent"),)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    data = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ShareLink(Base):
    """Shareable link for conversations."""

    __tablename__ = "share_links"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    share_token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    view_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConversationTopic(Base):
    """Auto-generated topic metadata for conversations."""

    __tablename__ = "conversation_topics"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    auto_generated = Column(Boolean, default=True)
    category = Column(String(50), nullable=True)
    keywords = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True, index=True)
    source = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KnowledgeEmbedding(Base):
    __tablename__ = "knowledge_embeddings"

    id = Column(Integer, primary_key=True)
    knowledge_id = Column(
        Integer, ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index = Column(Integer, nullable=True)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(1000), nullable=False)
    parameters_schema = Column(JSONB, nullable=False)
    output_schema = Column(JSONB, nullable=True)
    auth_scope = Column(String(40), nullable=True)
    rate_limit = Column(String(40), nullable=True)
    safety_filter = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_tool_name", "name"),)


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    course_code = Column(String(50), nullable=False, index=True)
    course_name = Column(String(200), nullable=False, index=True)
    credits = Column(String(10), nullable=True)

    course_nature = Column(String(50), nullable=True)
    course_type = Column(String(50), nullable=True)
    major = Column(String(100), nullable=True, index=True)

    is_exam_course = Column(Boolean, nullable=True)
    is_investigation_course = Column(Boolean, nullable=True)

    instructor = Column(String(200), nullable=True)
    offering_semester = Column(String(100), nullable=True)
    first_offering_semester = Column(String(100), nullable=True)

    total_hours = Column(String(10), nullable=True)
    lecture_hours = Column(String(10), nullable=True)
    experiment_hours = Column(String(10), nullable=True)
    practice_hours = Column(String(10), nullable=True)

    syllabus_status = Column(String(100), nullable=True)
    syllabus_content = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    data_source = Column(String(200), nullable=True)
    data_quality_score = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_verified = Column(DateTime(timezone=True), nullable=True)


class CourseRelationship(Base):
    __tablename__ = "course_relationships"

    id = Column(Integer, primary_key=True)
    from_course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type = Column(String(50), nullable=False)
    strength = Column(Integer, default=1)
    description = Column(String(200), nullable=True)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CourseLog(Base):
    __tablename__ = "course_logs"

    id = Column(Integer, primary_key=True)
    course_code = Column(String(50), nullable=False, index=True)
    operation_type = Column(String(50), nullable=False)
    field_name = Column(String(50), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    operator = Column(String(100), nullable=True)
    reason = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True)
    agent = Column(String(40), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    conversation_id = Column(Integer, nullable=True, index=True)
    profile_id = Column(String(100), nullable=True)
    profile_version = Column(String(40), nullable=True)
    request_text = Column(Text, nullable=True)
    plan_json = Column(JSONB, nullable=True)
    tool_summary = Column(JSONB, nullable=True)
    final_answer = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    cost = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
