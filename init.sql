-- FlyRank W3 · A2: PostgreSQL Initialization Script
-- Executed automatically on container first startup via /docker-entrypoint-initdb.d/

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast status and search queries
CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);

-- Seed initial tasks if the table is empty
INSERT INTO tasks (title, done)
SELECT 'Read the FastAPI docs', TRUE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = 1);

INSERT INTO tasks (title, done)
SELECT 'Build the CRUD API', FALSE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = 2);

INSERT INTO tasks (title, done)
SELECT 'Push to GitHub', FALSE
WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = 3);
