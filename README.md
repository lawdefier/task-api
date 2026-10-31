# Task API — FlyRank W3 · A2

A containerized, production-grade **CRUD API** built with **FastAPI**, **PostgreSQL in Docker**, and **Redis**, implementing a clean **Layered Architecture (Routes $\rightarrow$ Service $\rightarrow$ Repository)**.

This is the Week 3 Assignment 2 submission for FlyRank, demonstrating containerization, connection strings via `.env`, relational persistence with Docker volumes, and proving that switching storage backends touches **only one repository file** while leaving services and routes completely unchanged.

---

## Architecture & Layering

The application follows strict interface-driven decoupling:

```
[ HTTP Requests ]
       │
       ▼
[ Routes Layer ]         (main.py - Endpoints, HTTP status codes, validation)
       │
       ▼
[ Service Layer ]        (service.py - Domain logic, coordinating calls)
       │
       ▼
[ Repository Interface ] (repository.py - Abstract TaskRepository ABC)
       ├── PostgresTaskRepository (Primary: PostgreSQL via Docker)
       ├── SQLiteTaskRepository   (Fallback: Local file tasks.db)
       └── InMemoryTaskRepository (Legacy: In-memory array store)
```

> **Architecture Proof**:
> When switching from `InMemoryTaskRepository` to `PostgresTaskRepository`, **the Service layer (`service.py`) and Routes layer (`main.py`) remained 100% unchanged.** Only the repository implementation was swapped via dependency injection.

---

## Quick Start with Docker Compose

Start the entire stack (FastAPI App + PostgreSQL + Redis) with a single command:

```bash
docker compose up --build
```

- **FastAPI Application**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL Database**: `localhost:5432` (database: `taskdb`, user: `postgres`)
- **Redis Cache**: `localhost:6379`

To stop the containers:
```bash
docker compose down
```

---

## Environment Variables (.env)

Security best practice is enforced:
- **`.env`** contains sensitive connection strings and is strictly **gitignored**.
- **`.env.example`** is committed to the repository as a reference template:

```env
# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/taskdb

# Inside Docker Compose network:
# DATABASE_URL=postgresql://postgres:postgres@db:5432/taskdb

# Redis Cache / PubSub (Stretch Goal)
REDIS_URL=redis://localhost:6379/0

# App Server Port
PORT=8000
```

---

## Database Initialization & Volume Persistence

### Initial Schema (`init.sql`)
The PostgreSQL database is automatically initialized on the first container startup by mounting `./init.sql` into `/docker-entrypoint-initdb.d/init.sql`:

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    done BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
```

### Proving Persistence Across Restarts
Data persistence is guaranteed by the named Docker volume `postgres_data`:

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

**How Persistence Was Checked**:
1. Started the Docker stack:
   ```bash
   docker compose up -d
   ```
2. Created a new task:
   ```bash
   curl -X POST http://localhost:8000/tasks \
     -H "Content-Type: application/json" \
     -d '{"title": "Survive container restart"}'
   # Returns: {"id": 4, "title": "Survive container restart", "done": false}
   ```
3. Restarted both the application and database containers:
   ```bash
   docker compose down && docker compose up -d
   ```
4. Queried the newly created task:
   ```bash
   curl http://localhost:8000/tasks/4
   # Returns 200 OK: {"id": 4, "title": "Survive container restart", "done": false}
   ```
   **Result**: The data survived container tear-down and re-creation completely intact.

---

## Stretch Goals Completed

### 1. Redis Integration in Docker Compose
- Added `redis:7-alpine` container service to `docker-compose.yml`.
- Pinging Redis is integrated into the `/health` endpoint:
  ```bash
  curl http://localhost:8000/health
  ```
  ```json
  {
    "status": "ok",
    "storage": "PostgreSQL (Docker)",
    "database": "connected",
    "redis": "pong"
  }
  ```

### 2. Index Optimization & `EXPLAIN ANALYZE`
Created an index on `tasks(done)` (`idx_tasks_done`) and evaluated query execution before and after:

```bash
python explain_analyze.py
```

#### Before Index (Sequential Heap Scan)
```sql
EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = TRUE;

QUERY PLAN:
Seq Scan on tasks  (cost=0.00..18.50 rows=500 width=72) (actual time=0.012..0.085 rows=500 loops=1)
  Filter: done
  Rows Removed by Filter: 500
Planning Time: 0.075 ms
Execution Time: 0.120 ms
```

#### After Index (Bitmap Index Scan)
```sql
CREATE INDEX idx_tasks_done ON tasks(done);
EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = TRUE;

QUERY PLAN:
Bitmap Heap Scan on tasks  (cost=4.32..12.40 rows=500 width=72) (actual time=0.018..0.038 rows=500 loops=1)
  Recheck Cond: done
  ->  Bitmap Index Scan on idx_tasks_done  (cost=0.00..4.20 rows=500 width=0) (actual time=0.010..0.010 rows=500 loops=1)
        Index Cond: (done = true)
Planning Time: 0.082 ms
Execution Time: 0.052 ms
```

**Takeaway**: Cost decreased from **18.50 down to 12.40**, and execution time dropped by **over 55%**.

---

## API Endpoints Reference

| Method   | Path           | Status | Description |
|----------|----------------|--------|-------------|
| `GET`    | `/`            | `200`  | API metadata and architecture layer info |
| `GET`    | `/health`      | `200`  | Health probe checking DB & Redis |
| `GET`    | `/tasks`       | `200`  | List all tasks (`?done=`, `?search=`, `?sort=`) |
| `GET`    | `/tasks/{id}`  | `200` / `404` | Get single task by ID |
| `POST`   | `/tasks`       | `201` / `422` | Create task (`{"title": "..."}`) |
| `PUT`    | `/tasks/{id}`  | `200` / `404` / `422` | Update task title and completion |
| `DELETE` | `/tasks/{id}`  | `204` / `404` | Delete task by ID |
| `GET`    | `/stats`       | `200`  | Aggregated task statistics (total, done, open) |
| `POST`   | `/reset`       | `200`  | Reset to baseline seed tasks |

---

## Automated Verification Suite

Run all automated endpoint and persistence checks:
```bash
python test_checkpoints.py
```
