# 数据库结构对齐与映射（v1）

## 目标
- 以 PostgreSQL 为权威数据库。
- 合并 database/ 中已有结构与当前项目（backend/app/models.py）。
- 保持现有 API 兼容，逐步引入新表与字段。

## 现有模型概览（当前项目）
- users
- conversations
- messages
- memory_summaries
- user_profiles
- share_links
- conversation_topics

## 需合并模型概览（database/）
- users
- chat_sessions
- chat_messages
- sessions
- knowledge
- knowledge_embeddings
- tools
- courses
- course_relationships
- course_prerequisite_association
- course_related_association
- course_logs

## 核心映射与差异

### users
- 当前：`users(username, password_hash, created_at)`
- database：`users(username, email, hashed_password, is_active, created_at, updated_at)`
- 对齐建议：
  - `password_hash` 改为 `hashed_password` 或在模型层做别名映射（推荐统一为 `hashed_password`）。
  - 新增 `email`、`is_active`、`updated_at` 字段（保持兼容：email 可为空或设置默认值）。

### conversations vs chat_sessions
- 当前：`conversations(user_id, title, agent, status, created_at, updated_at)`
- database：`chat_sessions(user_id, title, created_at, updated_at)`
- 对齐建议：
  - 以 `conversations` 作为主表命名（保持现有 API）。
  - 在 schema 中补齐 `agent`、`status` 字段。
  - 迁移时将 `chat_sessions` 映射为 `conversations`，`agent` 默认填充（如来源未知可设为 `course` 或 `general`）。

### messages vs chat_messages
- 当前：`messages(conversation_id, role, content, created_at)`
- database：`chat_messages(session_id, user_id, role, content, created_at)`
- 对齐建议：
  - 主表继续使用 `messages`。
  - 新增 `user_id` 字段（保持兼容：已有逻辑可通过 conversation.user_id 反推）。
  - 迁移时 `session_id -> conversation_id`。

### sessions
- 当前：无该表（JWT 无状态）
- database：`sessions(user_id, token, expires_at, created_at)`
- 对齐建议：
  - 保留表用于可选的会话/令牌持久化，不强依赖。

### memory_summaries / user_profiles / share_links / conversation_topics
- 当前：已有表
- database：无对应
- 对齐建议：
  - 保持现有结构，不做合并映射。

### knowledge
- 当前：无
- database：`knowledge(title, content, category, source, is_active, created_at, updated_at)`
- 对齐建议：
  - 新增表到 Postgres，并在后端服务层逐步引入。

### knowledge_embeddings
- 当前：无
- database：`knowledge_embeddings(knowledge_id, chunk_index, chunk_text, embedding)`
- 对齐建议：
  - 新增表；embedding 字段建议从 `VARCHAR` 改为 `JSONB` 或 `FLOAT[]`（后续优化）。

### tools
- 当前：无
- database：`tools(name, description, parameters_schema JSON)`
- 对齐建议：
  - 新增表，作为工具定义与元数据的基础层。

### courses / course_relationships / course_logs
- 当前：无
- database：课程与关系表完整
- 对齐建议：
  - 全量引入；关系表保持原结构；course_logs 作为审计/变更记录。

## 迁移边界
- SQLite 数据需要全量迁移到 Postgres：`knowledge`、`tools`、`courses`、`course_relationships`。
- 空表（`users/chat_sessions/chat_messages/sessions/course_logs/knowledge_embeddings`）迁移为空即可。

## 兼容性重点
- 前端依赖 `/api/conversations?agent=...` 与 `/api/agents/{agent}/chat`，不能破坏。
- `agent` 字段必须在主对话表中存在。
- 用户模型增加 `email` 等字段时，需要保持注册/登录流程兼容。
