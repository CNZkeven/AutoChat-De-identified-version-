-- User table columns
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS major VARCHAR(100),
    ADD COLUMN IF NOT EXISTS grade INTEGER,
    ADD COLUMN IF NOT EXISTS gender VARCHAR(10);

CREATE INDEX IF NOT EXISTS ix_users_full_name ON users (full_name);
CREATE INDEX IF NOT EXISTS ix_users_major ON users (major);
CREATE INDEX IF NOT EXISTS ix_users_grade ON users (grade);
CREATE INDEX IF NOT EXISTS ix_users_gender ON users (gender);

-- System profile
CREATE TABLE IF NOT EXISTS user_system_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    model VARCHAR(100),
    prompt_version VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_system_profiles_user ON user_system_profiles (user_id);

-- Public profile
CREATE TABLE IF NOT EXISTS user_public_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    model VARCHAR(100),
    prompt_version VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_public_profiles_user ON user_public_profiles (user_id);

-- Course reports
CREATE TABLE IF NOT EXISTS user_course_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    offering_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    model VARCHAR(100),
    prompt_version VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_course_reports_user_offering ON user_course_reports (user_id, offering_id);

-- Academic report
CREATE TABLE IF NOT EXISTS user_academic_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    content TEXT NOT NULL,
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    model VARCHAR(100),
    prompt_version VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Graduation requirement snapshots
CREATE TABLE IF NOT EXISTS user_graduation_requirement_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    program_id INTEGER,
    grade_year INTEGER,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
