# 统一 Postgres Schema 设计（v1）

## 设计原则
- 兼容现有 API（/api/conversations 与 /api/agents/{agent}/chat）。
- 以当前项目的对话/记忆表为主干，新增知识库/课程/工具等业务表。
- 使用 PostgreSQL 原生类型（JSONB、TIMESTAMPTZ）。

## 核心表（对话/用户）

### users
- `id` SERIAL PRIMARY KEY
- `username` VARCHAR(64) UNIQUE NOT NULL
- `email` VARCHAR(100) UNIQUE NULL
- `hashed_password` VARCHAR(255) NOT NULL
- `is_active` BOOLEAN DEFAULT TRUE
- `created_at` TIMESTAMPTZ DEFAULT now()
- `updated_at` TIMESTAMPTZ DEFAULT now()

索引：`username`、`email`

### conversations
- `id` SERIAL PRIMARY KEY
- `user_id` INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
- `title` VARCHAR(200) NOT NULL
- `agent` VARCHAR(40) NOT NULL
- `status` VARCHAR(40) NOT NULL DEFAULT 'active'
- `created_at` TIMESTAMPTZ DEFAULT now()
- `updated_at` TIMESTAMPTZ DEFAULT now()

索引：`user_id`、`agent`、`status`

### messages
- `id` SERIAL PRIMARY KEY
- `conversation_id` INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE
- `user_id` INTEGER NULL REFERENCES users(id) ON DELETE SET NULL
- `role` VARCHAR(20) NOT NULL
- `content` TEXT NOT NULL
- `created_at` TIMESTAMPTZ DEFAULT now()

索引：`conversation_id`、`user_id`

### sessions（可选）
- `id` SERIAL PRIMARY KEY
- `user_id` INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
- `token` VARCHAR(500) UNIQUE NOT NULL
- `expires_at` TIMESTAMPTZ NOT NULL
- `created_at` TIMESTAMPTZ DEFAULT now()

## 记忆/画像/分享（保留现有结构）

### memory_summaries
- `id` SERIAL PRIMARY KEY
- `user_id` INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
- `agent` VARCHAR(40) NOT NULL
- `summary` TEXT NOT NULL
- `message_count` INTEGER DEFAULT 0
- `conversation_ids` JSONB DEFAULT '[]'
- `created_at` TIMESTAMPTZ DEFAULT now()
- `updated_at` TIMESTAMPTZ DEFAULT now()

索引：`(user_id, agent)`

### user_profiles
- `id` SERIAL PRIMARY KEY
- `user_id` INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
- `data` JSONB NOT NULL DEFAULT '{}'
- `updated_at` TIMESTAMPTZ DEFAULT now()

### share_links
- `id` SERIAL PRIMARY KEY
- `conversation_id` INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE
- `share_token` VARCHAR(64) UNIQUE NOT NULL
- `expires_at` TIMESTAMPTZ NULL
- `view_count` INTEGER DEFAULT 0
- `is_active` BOOLEAN DEFAULT TRUE
- `created_at` TIMESTAMPTZ DEFAULT now()

### conversation_topics
- `id` SERIAL PRIMARY KEY
- `conversation_id` INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE
- `auto_generated` BOOLEAN DEFAULT TRUE
- `category` VARCHAR(50) NULL
- `keywords` JSONB DEFAULT '[]'
- `created_at` TIMESTAMPTZ DEFAULT now()

## 知识库与 RAG

### knowledge
- `id` SERIAL PRIMARY KEY
- `title` VARCHAR(300) NOT NULL
- `content` TEXT NOT NULL
- `category` VARCHAR(100) NULL
- `source` VARCHAR(500) NULL
- `is_active` BOOLEAN DEFAULT TRUE
- `created_at` TIMESTAMPTZ DEFAULT now()
- `updated_at` TIMESTAMPTZ DEFAULT now()

索引：`category`、`is_active`

### knowledge_embeddings
- `id` SERIAL PRIMARY KEY
- `knowledge_id` INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE
- `chunk_index` INTEGER NULL
- `chunk_text` TEXT NOT NULL
- `embedding` JSONB NOT NULL
- `created_at` TIMESTAMPTZ DEFAULT now()

索引：`knowledge_id`

> 备注：如后续引入 pgvector，可将 embedding 迁移为 vector 类型。

## 课程与关系

### courses
- `id` SERIAL PRIMARY KEY
- `course_code` VARCHAR(50) NOT NULL
- `course_name` VARCHAR(200) NOT NULL
- `credits` VARCHAR(10) NULL
- `course_nature` VARCHAR(50) NULL
- `course_type` VARCHAR(50) NULL
- `major` VARCHAR(100) NULL
- `is_exam_course` BOOLEAN NULL
- `is_investigation_course` BOOLEAN NULL
- `instructor` VARCHAR(200) NULL
- `offering_semester` VARCHAR(100) NULL
- `first_offering_semester` VARCHAR(100) NULL
- `total_hours` VARCHAR(10) NULL
- `lecture_hours` VARCHAR(10) NULL
- `experiment_hours` VARCHAR(10) NULL
- `practice_hours` VARCHAR(10) NULL
- `syllabus_status` VARCHAR(100) NULL
- `syllabus_content` TEXT NULL
- `is_active` BOOLEAN DEFAULT TRUE
- `data_source` VARCHAR(200) NULL
- `data_quality_score` INTEGER NULL
- `notes` TEXT NULL
- `created_at` TIMESTAMPTZ DEFAULT now()
- `updated_at` TIMESTAMPTZ DEFAULT now()
- `last_verified` TIMESTAMPTZ NULL

索引：`course_code`、`course_name`、`major`

### course_relationships
- `id` SERIAL PRIMARY KEY
- `from_course_id` INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE
- `to_course_id` INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE
- `relationship_type` VARCHAR(50) NOT NULL
- `strength` INTEGER DEFAULT 1
- `description` VARCHAR(200) NULL
- `is_confirmed` BOOLEAN DEFAULT FALSE
- `created_at` TIMESTAMPTZ DEFAULT now()
- `updated_at` TIMESTAMPTZ DEFAULT now()

索引：`from_course_id`、`to_course_id`

### course_prerequisite_association
- `from_course_id` INTEGER REFERENCES courses(id) ON DELETE CASCADE
- `to_course_id` INTEGER REFERENCES courses(id) ON DELETE CASCADE

### course_related_association
- `course_id_1` INTEGER REFERENCES courses(id) ON DELETE CASCADE
- `course_id_2` INTEGER REFERENCES courses(id) ON DELETE CASCADE

### course_logs
- `id` SERIAL PRIMARY KEY
- `course_code` VARCHAR(50) NOT NULL
- `operation_type` VARCHAR(50) NOT NULL
- `field_name` VARCHAR(50) NULL
- `old_value` TEXT NULL
- `new_value` TEXT NULL
- `operator` VARCHAR(100) NULL
- `reason` VARCHAR(200) NULL
- `created_at` TIMESTAMPTZ DEFAULT now()

## tools
- `id` SERIAL PRIMARY KEY
- `name` VARCHAR(255) UNIQUE NOT NULL
- `description` VARCHAR(1000) NOT NULL
- `parameters_schema` JSONB NOT NULL
- `created_at` TIMESTAMPTZ DEFAULT now()
