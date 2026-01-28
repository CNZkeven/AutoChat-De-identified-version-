from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    func,
)
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
    full_name = Column(String(100), nullable=True, index=True)
    major = Column(String(100), nullable=True, index=True)
    grade = Column(Integer, nullable=True, index=True)
    gender = Column(String(10), nullable=True, index=True)
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


class UserSystemProfile(Base):
    __tablename__ = "user_system_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    source_snapshot = Column(JSONB, nullable=False, default=dict)
    model = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_user_system_profiles_user", "user_id"),)


class UserPublicProfile(Base):
    __tablename__ = "user_public_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    source_snapshot = Column(JSONB, nullable=False, default=dict)
    model = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_user_public_profiles_user", "user_id"),)


class UserCourseReport(Base):
    __tablename__ = "user_course_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    offering_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)
    source_snapshot = Column(JSONB, nullable=False, default=dict)
    model = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_user_course_reports_user_offering", "user_id", "offering_id"),)


class UserAcademicReport(Base):
    __tablename__ = "user_academic_reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    source_snapshot = Column(JSONB, nullable=False, default=dict)
    model = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserGraduationRequirementSnapshot(Base):
    __tablename__ = "user_graduation_requirement_snapshots"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    program_id = Column(Integer, nullable=True, index=True)
    grade_year = Column(Integer, nullable=True, index=True)
    data = Column(JSONB, nullable=False, default=dict)
    source_snapshot = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
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


class AgentRunTrace(Base):
    __tablename__ = "agent_run_traces"

    id = Column(Integer, primary_key=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    agent = Column(String(40), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    conversation_id = Column(Integer, nullable=True, index=True)
    user_message_id = Column(Integer, nullable=True, index=True)
    request_text = Column(Text, nullable=True)
    trace = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DmStudent(Base):
    __tablename__ = "students"
    __table_args__ = {"schema": "dm"}

    student_id = Column(Integer, primary_key=True)
    student_no = Column(String(50), nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    program_id = Column(Integer, nullable=True)
    grade_id = Column(Integer, nullable=True)
    class_name = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmStudentIdentityMap(Base):
    __tablename__ = "student_identity_map"
    __table_args__ = (
        Index("idx_dm_identity_user", "user_id"),
        Index("idx_dm_identity_student_no", "student_no"),
        {"schema": "dm"},
    )

    user_id = Column(Integer, primary_key=True)
    student_no = Column(String(50), nullable=False)
    student_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DmProgram(Base):
    __tablename__ = "programs"
    __table_args__ = {"schema": "dm"}

    program_id = Column(Integer, primary_key=True)
    program_code = Column(String(50), nullable=True)
    name = Column(String(255), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmProgramVersion(Base):
    __tablename__ = "program_versions"
    __table_args__ = {"schema": "dm"}

    program_version_id = Column(Integer, primary_key=True)
    program_id = Column(Integer, nullable=False, index=True)
    version_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmProgramVersionCourse(Base):
    __tablename__ = "program_version_courses"
    __table_args__ = (
        Index("idx_dm_pvc_program_version", "program_version_id"),
        Index("idx_dm_pvc_course", "course_id"),
        {"schema": "dm"},
    )

    program_version_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, primary_key=True)
    course_category = Column(String(50), nullable=True)
    course_nature = Column(String(50), nullable=True)
    planned_semester = Column(String(20), nullable=True)
    plan_remarks = Column(Text, nullable=True)
    display_order_label = Column(String(50), nullable=True)
    display_order_primary = Column(Integer, nullable=True)
    display_order_secondary = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmCourse(Base):
    __tablename__ = "courses"
    __table_args__ = {"schema": "dm"}

    course_id = Column(Integer, primary_key=True)
    course_code = Column(String(50), nullable=True, index=True)
    course_name = Column(String(255), nullable=False)
    credits = Column(Numeric(4, 2), nullable=True)
    total_hours = Column(Integer, nullable=True)
    lecture_hours = Column(Integer, nullable=True)
    experiment_hours = Column(Integer, nullable=True)
    practice_hours = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmAcademicTerm(Base):
    __tablename__ = "academic_terms"
    __table_args__ = {"schema": "dm"}

    term_id = Column(Integer, primary_key=True)
    term_name = Column(String(100), nullable=False)
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)
    term_index = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmCourseOffering(Base):
    __tablename__ = "course_offerings"
    __table_args__ = (
        Index("idx_dm_offering_term", "term_id"),
        Index("idx_dm_offering_course", "course_id"),
        {"schema": "dm"},
    )

    offering_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, nullable=False)
    term_id = Column(Integer, nullable=False)
    teacher_id = Column(Integer, nullable=True)
    teacher_name = Column(String(100), nullable=True)
    section_name = Column(String(50), nullable=True)
    class_number = Column(String(100), nullable=True)
    program_id = Column(Integer, nullable=True)
    grade_year = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmEnrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        Index("idx_dm_enrollment_student", "student_no"),
        {"schema": "dm"},
    )

    offering_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, primary_key=True)
    student_no = Column(String(50), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmStudentScore(Base):
    __tablename__ = "student_scores"
    __table_args__ = (
        Index("idx_dm_score_student", "student_no"),
        Index("idx_dm_score_offering", "offering_id"),
        {"schema": "dm"},
    )

    offering_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, primary_key=True)
    student_no = Column(String(50), nullable=False)
    total_score = Column(Numeric(5, 2), nullable=True)
    grade_text = Column(String(50), nullable=True)
    score_source = Column(String(20), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmSectionGradeSummary(Base):
    __tablename__ = "section_grade_summary"
    __table_args__ = {"schema": "dm"}

    offering_id = Column(Integer, primary_key=True)
    term_id = Column(Integer, nullable=True)
    n_students = Column(Integer, nullable=False, default=0)
    avg_score = Column(Numeric(5, 2), nullable=True)
    min_score = Column(Numeric(5, 2), nullable=True)
    max_score = Column(Numeric(5, 2), nullable=True)
    dist_json = Column(JSONB, nullable=False, default=dict)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())


class DmSyllabusVersion(Base):
    __tablename__ = "syllabus_versions"
    __table_args__ = {"schema": "dm"}

    syllabus_version_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, nullable=False)
    version_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    syllabus_type = Column(String(20), nullable=True)
    status = Column(String(20), nullable=True)
    basic_info = Column(Text, nullable=True)
    process_requirements = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmCourseObjective(Base):
    __tablename__ = "course_objectives"
    __table_args__ = (
        Index("idx_dm_objective_offering", "offering_id"),
        Index("idx_dm_objective_course", "course_id"),
        {"schema": "dm"},
    )

    objective_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, nullable=True)
    offering_id = Column(Integer, nullable=True)
    syllabus_version_id = Column(Integer, nullable=True)
    objective_index = Column(String(20), nullable=True)
    description = Column(Text, nullable=False)
    objective_type = Column(String(20), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmGraduationRequirement(Base):
    __tablename__ = "graduation_requirements"
    __table_args__ = (
        Index("idx_dm_gr_requirement_program", "program_id"),
        {"schema": "dm"},
    )

    requirement_id = Column(Integer, primary_key=True)
    program_id = Column(Integer, nullable=False, index=True)
    requirement_index = Column(String(50), nullable=True)
    description = Column(Text, nullable=False)
    level = Column(Integer, nullable=True)
    parent_id = Column(Integer, nullable=True)
    training_program_version_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmObjectiveRequirementMapping(Base):
    __tablename__ = "objective_requirement_mapping"
    __table_args__ = (
        Index("idx_dm_objective_requirement_requirement", "requirement_id"),
        {"schema": "dm"},
    )

    objective_id = Column(Integer, primary_key=True)
    requirement_id = Column(Integer, primary_key=True)
    weight = Column(Numeric(3, 2), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmStudentObjectiveAchievement(Base):
    __tablename__ = "student_objective_achievements"
    __table_args__ = (
        Index("idx_dm_student_objective_student", "student_no"),
        Index("idx_dm_student_objective_offering", "offering_id"),
        {"schema": "dm"},
    )

    offering_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, primary_key=True)
    objective_id = Column(Integer, primary_key=True)
    student_no = Column(String(50), nullable=False)
    achievement_score = Column(Numeric(5, 4), nullable=False)
    total_score = Column(Numeric(5, 2), nullable=False)
    max_score = Column(Numeric(5, 2), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class DmSectionObjectiveSummary(Base):
    __tablename__ = "section_objective_summary"
    __table_args__ = {"schema": "dm"}

    offering_id = Column(Integer, primary_key=True)
    objective_id = Column(Integer, primary_key=True)
    n_students = Column(Integer, nullable=False, default=0)
    avg_score = Column(Numeric(5, 4), nullable=True)
    min_score = Column(Numeric(5, 4), nullable=True)
    max_score = Column(Numeric(5, 4), nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())


class OpsSyncWatermark(Base):
    __tablename__ = "sync_watermark"
    __table_args__ = {"schema": "ops"}

    source_name = Column(String(50), primary_key=True)
    entity_name = Column(String(50), primary_key=True)
    last_updated_at = Column(DateTime(timezone=True), nullable=True)
    last_pk = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OpsSyncJobLog(Base):
    __tablename__ = "sync_job_log"
    __table_args__ = {"schema": "ops"}

    job_id = Column(String(36), primary_key=True)
    job_name = Column(String(100), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False)
    detail = Column(JSONB, nullable=False, default=dict)
