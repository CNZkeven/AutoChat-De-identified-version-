-- Graduation requirements in dm schema
CREATE TABLE IF NOT EXISTS dm.graduation_requirements (
    requirement_id INTEGER PRIMARY KEY,
    program_id INTEGER NOT NULL,
    requirement_index VARCHAR(50),
    description TEXT NOT NULL,
    level INTEGER,
    parent_id INTEGER,
    training_program_version_id INTEGER,
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_dm_gr_requirement_program ON dm.graduation_requirements (program_id);

-- Objective requirement mapping in dm schema
CREATE TABLE IF NOT EXISTS dm.objective_requirement_mapping (
    objective_id INTEGER NOT NULL,
    requirement_id INTEGER NOT NULL,
    weight NUMERIC(3,2),
    updated_at TIMESTAMPTZ,
    PRIMARY KEY (objective_id, requirement_id)
);

CREATE INDEX IF NOT EXISTS idx_dm_objective_requirement_requirement ON dm.objective_requirement_mapping (requirement_id);
