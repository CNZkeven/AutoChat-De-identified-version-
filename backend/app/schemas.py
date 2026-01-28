from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    email: str | None = Field(default=None, max_length=100)


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    full_name: str | None = None
    major: str | None = None
    grade: int | None = None
    gender: str | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str


class ConversationOut(BaseModel):
    id: int
    user_id: int
    title: str
    agent: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str | None = None
    messages: list[ChatMessage] | None = None
    selected_messages: list[ChatMessage] | None = None


class KnowledgeCreate(BaseModel):
    title: str
    content: str
    category: str | None = None
    source: str | None = None
    is_active: bool | None = True


class KnowledgeUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    source: str | None = None
    is_active: bool | None = None


class KnowledgeOut(BaseModel):
    id: int
    title: str
    content: str
    category: str | None = None
    source: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class KnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = 5


class KnowledgeContextResponse(BaseModel):
    context: str
    total: int


class ToolCreate(BaseModel):
    name: str
    description: str
    parameters_schema: dict


class ToolUpdate(BaseModel):
    description: str | None = None
    parameters_schema: dict | None = None


class ToolOut(BaseModel):
    id: int
    name: str
    description: str
    parameters_schema: dict
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    course_code: str
    course_name: str
    credits: str | None = None
    course_nature: str | None = None
    course_type: str | None = None
    major: str | None = None
    is_exam_course: bool | None = None
    is_investigation_course: bool | None = None
    instructor: str | None = None
    offering_semester: str | None = None
    first_offering_semester: str | None = None
    total_hours: str | None = None
    lecture_hours: str | None = None
    experiment_hours: str | None = None
    practice_hours: str | None = None
    syllabus_status: str | None = None
    syllabus_content: str | None = None
    is_active: bool | None = True
    data_source: str | None = None
    data_quality_score: int | None = None
    notes: str | None = None
    last_verified: datetime | None = None


class CourseUpdate(BaseModel):
    course_code: str | None = None
    course_name: str | None = None
    credits: str | None = None
    course_nature: str | None = None
    course_type: str | None = None
    major: str | None = None
    is_exam_course: bool | None = None
    is_investigation_course: bool | None = None
    instructor: str | None = None
    offering_semester: str | None = None
    first_offering_semester: str | None = None
    total_hours: str | None = None
    lecture_hours: str | None = None
    experiment_hours: str | None = None
    practice_hours: str | None = None
    syllabus_status: str | None = None
    syllabus_content: str | None = None
    is_active: bool | None = None
    data_source: str | None = None
    data_quality_score: int | None = None
    notes: str | None = None
    last_verified: datetime | None = None


class CourseOut(BaseModel):
    id: int
    course_code: str
    course_name: str
    credits: str | None = None
    course_nature: str | None = None
    course_type: str | None = None
    major: str | None = None
    is_exam_course: bool | None = None
    is_investigation_course: bool | None = None
    instructor: str | None = None
    offering_semester: str | None = None
    first_offering_semester: str | None = None
    total_hours: str | None = None
    lecture_hours: str | None = None
    experiment_hours: str | None = None
    practice_hours: str | None = None
    syllabus_status: str | None = None
    syllabus_content: str | None = None
    is_active: bool | None = None
    data_source: str | None = None
    data_quality_score: int | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_verified: datetime | None = None

    class Config:
        from_attributes = True


class DMSyncRequest(BaseModel):
    job_name: str = "dm_sync_manual"
    entities: list[str] | None = None
    term_window: list[str] | None = None
    batch_size: int | None = None


class DMSyncResponse(BaseModel):
    job_id: str
    job_name: str
    status: str
    detail: dict


class AdminUserOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    is_active: bool | None = None
    full_name: str | None = None
    major: str | None = None
    grade: int | None = None
    gender: str | None = None

    class Config:
        from_attributes = True


class AdminUserProfileOut(BaseModel):
    user_id: int
    data: dict


class AdminUserProfilesOut(BaseModel):
    user_id: int
    system_profile: str | None = None
    public_profile: str | None = None
    system_updated_at: datetime | None = None
    public_updated_at: datetime | None = None


class AdminUserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    major: str | None = None
    grade: int | None = None
    gender: str | None = None
    is_active: bool | None = None


class AdminUserImportResult(BaseModel):
    total: int
    created: int
    updated: int
    failed: int
    errors: list[str] = Field(default_factory=list)


class UserProfileOut(BaseModel):
    content: str | None = None
    updated_at: datetime | None = None


class UserCourseOut(BaseModel):
    offering_id: int
    class_number: str | None = None
    course_code: str
    course_name: str
    teacher_name: str | None = None
    total_score: float | None = None
    grade_text: str | None = None
    percentile: float | None = None


class UserCourseObjectiveOut(BaseModel):
    objective_id: int
    objective_index: str | None = None
    description: str
    achievement_score: float | None = None
    total_score: float | None = None
    max_score: float | None = None
    percentile: float | None = None


class UserCourseReportOut(BaseModel):
    content: str | None = None
    updated_at: datetime | None = None


class UserAcademicReportOut(BaseModel):
    content: str | None = None
    updated_at: datetime | None = None


class UserGraduationRequirementOut(BaseModel):
    data: dict
    updated_at: datetime | None = None


class AdminAgentOut(BaseModel):
    id: str
    title: str
    greeting: str | None = None
    profile: dict | None = None
    prompt: str | None = None
    prompt_template_path: str | None = None


class AdminConversationOut(BaseModel):
    id: int
    user_id: int
    title: str
    agent: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class AdminRunSummaryOut(BaseModel):
    id: int
    agent_run_id: int | None = None
    conversation_id: int | None = None
    user_message_id: int | None = None
    request_text: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class AdminRunDetailOut(BaseModel):
    id: int
    agent_run_id: int | None = None
    conversation_id: int | None = None
    user_message_id: int | None = None
    request_text: str | None = None
    trace: list[dict] = []
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class AdminDebugRunRequest(BaseModel):
    user_id: int
    agent: str
    conversation_id: int | None = None
    style: str | None = None
    message: str | None = None
    messages: list[ChatMessage] | None = None
    selected_messages: list[ChatMessage] | None = None


class AdminDebugRunResponse(BaseModel):
    conversation_id: int
    trace_id: int
    final_text: str | None = None
