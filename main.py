"""
Task API — FlyRank W3 · A2
Layered architecture: Routes -> Service -> Repository.
Supports PostgreSQL (in Docker), Redis ping (stretch goal), and local fallbacks.
"""

from fastapi import FastAPI, HTTPException, status, Query, Depends
from typing import Optional
from pathlib import Path
import os
from dotenv import load_dotenv

from models import TaskIn, TaskOut
from repository import (
    TaskRepository,
    PostgresTaskRepository,
    SQLiteTaskRepository,
    InMemoryTaskRepository,
)
from service import TaskService

# Load environment configuration (.env)
load_dotenv()

app = FastAPI(
    title="Task API",
    description=(
        "Layered CRUD API built for FlyRank W3 · A2. "
        "Separates Routes -> Service -> Repository. "
        "Supports PostgreSQL in Docker with volume persistence and optional Redis cache."
    ),
    version="3.0",
)

# ──────────────────────────────────────────────
# Dependency Injection: Repository & Service Setup
# ──────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
DB_PATH = Path(__file__).parent / "tasks.db"

_active_repo: Optional[TaskRepository] = None
_storage_type = "unknown"


def get_task_repository() -> TaskRepository:
    """
    Factory creating the appropriate repository.
    Default: PostgresTaskRepository using DATABASE_URL from .env.
    Fallback: SQLiteTaskRepository for offline local execution.
    """
    global _active_repo, _storage_type
    if _active_repo is not None:
        return _active_repo

    if DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")):
        try:
            repo = PostgresTaskRepository(DATABASE_URL)
            if repo.check_health():
                _active_repo = repo
                _storage_type = "PostgreSQL (Docker)"
                return _active_repo
        except Exception:
            pass

    # Local fallback if Docker Postgres is offline
    _active_repo = SQLiteTaskRepository(DB_PATH)
    _storage_type = "SQLite (Local fallback)"
    return _active_repo


def get_task_service(repo: TaskRepository = Depends(get_task_repository)) -> TaskService:
    """Injects TaskService configured with the active repository."""
    return TaskService(repository=repo)


def ping_redis() -> str:
    """Optional Stretch Goal: Ping Redis if configured."""
    if not REDIS_URL:
        return "not_configured"
    try:
        import redis
        client = redis.from_url(REDIS_URL, socket_timeout=1.0)
        return "pong" if client.ping() else "offline"
    except Exception:
        return "offline"


# ──────────────────────────────────────────────
# Meta Endpoints
# ──────────────────────────────────────────────

@app.get(
    "/",
    summary="API Info",
    description="Describes the API, storage backend, and available endpoints.",
    tags=["Meta"],
)
def root():
    get_task_repository()
    return {
        "name": "Task API",
        "version": "3.0",
        "architecture": "Layered (Routes -> Service -> Repository)",
        "storage": _storage_type,
        "endpoints": ["/tasks", "/tasks/{id}", "/stats", "/reset", "/health"],
    }


@app.get(
    "/health",
    summary="Health check",
    description="Checks API status, database connection, and optional Redis ping.",
    tags=["Meta"],
)
def health(service: TaskService = Depends(get_task_service)):
    db_healthy = service.is_healthy()
    redis_status = ping_redis()
    if not db_healthy:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database health check failed",
        )
    return {
        "status": "ok",
        "storage": _storage_type,
        "database": "connected",
        "redis": redis_status,
    }


# ──────────────────────────────────────────────
# CRUD Endpoints (UNCHANGED from earlier assignments)
# ──────────────────────────────────────────────

@app.get(
    "/tasks",
    response_model=list[TaskOut],
    summary="List all tasks",
    description="Fetches tasks via TaskService with optional completion filter and substring search.",
    tags=["Tasks"],
)
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search keyword in title"),
    sort: Optional[str] = Query("id", description="Sort field: 'id' or 'title'"),
    service: TaskService = Depends(get_task_service),
):
    return service.list_tasks(done=done, search=search, sort=sort)


@app.get(
    "/tasks/{task_id}",
    response_model=TaskOut,
    summary="Get single task",
    description="Fetches one task by its ID. Returns 404 if not found.",
    tags=["Tasks"],
)
def get_task(task_id: int, service: TaskService = Depends(get_task_service)):
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return task


@app.post(
    "/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    description="Creates a new task. Requires a non-empty title. Returns 201 Created.",
    tags=["Tasks"],
)
def create_task(body: TaskIn, service: TaskService = Depends(get_task_service)):
    return service.create_task(title=body.title, done=body.done)


@app.put(
    "/tasks/{task_id}",
    response_model=TaskOut,
    summary="Update task",
    description="Updates task title and/or done status. Returns 404 if task not found.",
    tags=["Tasks"],
)
def update_task(task_id: int, body: TaskIn, service: TaskService = Depends(get_task_service)):
    updated = service.update_task(task_id=task_id, title=body.title, done=body.done)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return updated


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Removes a task by ID. Returns 204 No Content.",
    tags=["Tasks"],
)
def delete_task(task_id: int, service: TaskService = Depends(get_task_service)):
    deleted = service.delete_task(task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return None


# ──────────────────────────────────────────────
# Extras: Stats & Reset
# ──────────────────────────────────────────────

@app.get(
    "/stats",
    summary="Task statistics",
    description="Returns aggregate counts (total, completed, open) calculated in storage.",
    tags=["Extras"],
)
def stats(service: TaskService = Depends(get_task_service)):
    return service.get_stats()


@app.post(
    "/reset",
    summary="Reset tasks",
    description="Restores the initial seed data.",
    tags=["Extras"],
)
def reset(service: TaskService = Depends(get_task_service)):
    service.reset_database()
    return {"message": "Storage reset to initial seed tasks"}
