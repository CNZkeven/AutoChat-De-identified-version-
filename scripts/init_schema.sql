CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    agent VARCHAR(40) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory_summaries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent VARCHAR(40) NOT NULL,
    summary TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    conversation_ids JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_memory_user_agent ON memory_summaries (user_id, agent);

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS share_links (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    share_token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NULL,
    view_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_topics (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    auto_generated BOOLEAN DEFAULT TRUE,
    category VARCHAR(50) NULL,
    keywords JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    source VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id SERIAL PRIMARY KEY,
    knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    chunk_text TEXT NOT NULL,
    embedding JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description VARCHAR(1000) NOT NULL,
    parameters_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tool_name ON tools (name);

CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(50) NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    credits VARCHAR(10),
    course_nature VARCHAR(50),
    course_type VARCHAR(50),
    major VARCHAR(100),
    is_exam_course BOOLEAN,
    is_investigation_course BOOLEAN,
    instructor VARCHAR(200),
    offering_semester VARCHAR(100),
    first_offering_semester VARCHAR(100),
    total_hours VARCHAR(10),
    lecture_hours VARCHAR(10),
    experiment_hours VARCHAR(10),
    practice_hours VARCHAR(10),
    syllabus_status VARCHAR(100),
    syllabus_content TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    data_source VARCHAR(200),
    data_quality_score INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_verified TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS course_relationships (
    id SERIAL PRIMARY KEY,
    from_course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    to_course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    strength INTEGER DEFAULT 1,
    description VARCHAR(200),
    is_confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_prerequisite_association (
    from_course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    to_course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS course_related_association (
    course_id_1 INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    course_id_2 INTEGER REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS course_logs (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(50) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(50),
    old_value TEXT,
    new_value TEXT,
    operator VARCHAR(100),
    reason VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
