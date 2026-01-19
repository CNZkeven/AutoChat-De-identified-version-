# SQLite -> Postgres 迁移策略（v1）

## 目标
- 将 `database/agent_db.sqlite` 的全量数据迁移到 Postgres（作为新统一 schema 的权威数据）。

## 迁移顺序（按依赖）
1) users
2) conversations（由 chat_sessions 映射）
3) messages（由 chat_messages 映射）
4) knowledge
5) knowledge_embeddings
6) tools
7) courses
8) course_relationships
9) course_prerequisite_association
10) course_related_association
11) sessions
12) course_logs

## 映射与转换规则
- users：
  - `hashed_password` 直接写入
  - `email` 保持原值（如缺失可设置为空或默认占位，需策略确认）
- chat_sessions -> conversations：
  - `id` 保留
  - `user_id` 保留
  - `title` 保留
  - `agent` 需要默认值（待确认）
  - `status` 默认 `active`
  - `created_at/updated_at` 保留
- chat_messages -> messages：
  - `id` 保留
  - `session_id -> conversation_id`
  - `user_id` 保留（允许为空时置 NULL）
  - 其余字段保留
- knowledge / knowledge_embeddings / tools / courses：直接迁移
- course_relationships / 关联表 / logs：直接迁移
- sessions：直接迁移（若未来不使用可保留数据）

## 技术路线
- 建议新增迁移脚本（Python/SQLAlchemy 或 psycopg）
- 连接信息：
  - SQLite: `sqlite:///database/agent_db.sqlite`
  - Postgres: 使用当前 `DATABASE_URL`
- 迁移时显式写入 `id`，迁移后更新 Postgres 序列：
  - `SELECT setval(pg_get_serial_sequence('table', 'id'), (SELECT COALESCE(MAX(id), 1) FROM table));`

## 校验与回滚
- 迁移后比对各表行数
- 抽样验证 `courses/knowledge/tools` 内容正确
- 若失败：清空目标表并重跑迁移脚本

## 待确认事项
- chat_sessions 映射 conversations 时的 `agent` 默认值（见下一步确认）。
- users.email 缺失时的填充策略（可空/占位/跳过）。
