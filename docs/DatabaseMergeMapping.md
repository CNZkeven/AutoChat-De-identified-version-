# 数据库结构对齐与映射（v1）

## 目标
- 以 PostgreSQL 为权威数据库。
- 已完成与历史 database 结构的合并，现统一维护于 backend/app/models.py。
- 该文档作为历史映射记录，供回溯参考。

## 现有模型概览（当前项目）
- users
- conversations
- messages
- memory_summaries
- user_profiles
- share_links
- conversation_topics
- knowledge
- knowledge_embeddings
- tools
- courses
- course_relationships
- course_prerequisite_association
- course_related_association
- course_logs

## 历史合并模型概览（已并入）
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
- 历史结构：`users(username, email, hashed_password, is_active, created_at, updated_at)`
- 对齐建议：
  - `password_hash` 改为 `hashed_password` 或在模型层做别名映射（推荐统一为 `hashed_password`）。
  - 新增 `email`、`is_active`、`updated_at` 字段（保持兼容：email 可为空或设置默认值）。

### conversations vs chat_sessions
- 当前：`conversations(user_id, title, agent, status, created_at, updated_at)`
- 历史结构：`chat_sessions(user_id, title, created_at, updated_at)`
- 对齐建议：
  - 以 `conversations` 作为主表命名（保持现有 API）。
  - 在 schema 中补齐 `agent`、`status` 字段。
  - 迁移时将 `chat_sessions` 映射为 `conversations`，`agent` 默认填充（如来源未知可设为 `course` 或 `general`）。

### messages vs chat_messages
- 当前：`messages(conversation_id, role, content, created_at)`
- 历史结构：`chat_messages(session_id, user_id, role, content, created_at)`
- 对齐建议：
  - 主表继续使用 `messages`。
  - 新增 `user_id` 字段（保持兼容：已有逻辑可通过 conversation.user_id 反推）。
  - 迁移时 `session_id -> conversation_id`。

### sessions
- 当前：无该表（JWT 无状态）
- 历史结构：`sessions(user_id, token, expires_at, created_at)`
- 对齐建议：
  - 保留表用于可选的会话/令牌持久化，不强依赖。

### memory_summaries / user_profiles / share_links / conversation_topics
- 当前：已有表
- 历史结构：无对应
- 对齐建议：
  - 保持现有结构，不做合并映射。

### knowledge
- 当前：`knowledge(title, content, category, source, is_active, created_at, updated_at)`（已合并）
- 历史结构：`knowledge(title, content, category, source, is_active, created_at, updated_at)`
- 状态：
  - 已并入统一 schema。

### knowledge_embeddings
- 当前：`knowledge_embeddings(knowledge_id, chunk_index, chunk_text, embedding)`（已合并）
- 历史结构：`knowledge_embeddings(knowledge_id, chunk_index, chunk_text, embedding)`
- 状态：
  - 已并入统一 schema。

### tools
- 当前：`tools(name, description, parameters_schema, created_at)`（已合并）
- 历史结构：`tools(name, description, parameters_schema JSON)`
- 状态：
  - 已并入统一 schema。

### courses / course_relationships / course_logs
- 当前：课程与关系表已合并
- 历史结构：课程与关系表完整
- 状态：
  - 已并入统一 schema。

## 迁移状态
- SQLite 迁移脚本已移除；如需历史数据请从备份或历史版本恢复。

## 兼容性重点
- 前端依赖 `/api/conversations?agent=...` 与 `/api/agents/{agent}/chat`，不能破坏。
- `agent` 字段必须在主对话表中存在。
- 用户模型增加 `email` 等字段时，需要保持注册/登录流程兼容。
