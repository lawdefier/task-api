"""
Task API — FlyRank W2 · A1
A full CRUD API for managing to-do tasks, built with FastAPI.
Data lives in memory (no database) — intentionally.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, field_validator
from typing import Optional
import copy

# ──────────────────────────────────────────────
# App setup (Stage 0 & 1)
# ──────────────────────────────────────────────

app = FastAPI(
    title="Task API",
    description=(
        "A simple in-memory to-do list API built for FlyRank Week 2. "
        "Supports full CRUD — create, read, update, and delete tasks. "
        "Data resets on server restart (no database — that's Week 3)."
    ),
    version="1.0",
)

# ──────────────────────────────────────────────
# In-memory "database" — Stage 2
# ──────────────────────────────────────────────

SEED_TASKS = [
    {"id": 1, "title": "Read the FastAPI docs", "done": True},
    {"id": 2, "title": "Build the CRUD API",    "done": False},
    {"id": 3, "title": "Push to GitHub",         "done": False},
]

tasks: list[dict] = copy.deepcopy(SEED_TASKS)
next_id: int = 4  # tracks the next free id


# ──────────────────────────────────────────────
# Pydantic models — request / response shapes
# ──────────────────────────────────────────────

class TaskIn(BaseModel):
    """Body accepted by POST /tasks and PUT /tasks/{id}."""
    title: str
    done: Optional[bool] = False

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()


class TaskOut(BaseModel):
    """Shape of every task returned by the API."""
    id: int
    title: str
    done: bool


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def find_task(task_id: int) -> dict:
    """Return the task dict or raise 404."""
    for t in tasks:
        if t["id"] == task_id:
            return t
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )


# ──────────────────────────────────────────────
# Stage 1 — root & health
# ──────────────────────────────────────────────

@app.get(
    "/",
    summary="API info",
    description="Returns the API name, version, and available endpoint paths.",
    tags=["Meta"],
)
def root():
    """Describe this API at a glance."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get(
    "/health",
    summary="Health check",
    description="Returns `{status: ok}`. Real services use this to confirm the server is alive.",
    tags=["Meta"],
)
def health():
    """Liveness probe — returns ok when the server is running."""
    return {"status": "ok"}


# ──────────────────────────────────────────────
# Stage 2 — Read (GET /tasks, GET /tasks/{id})
# ──────────────────────────────────────────────

@app.get(
    "/tasks",
    response_model=list[TaskOut],
    summary="List all tasks",
    description=(
        "Returns every task in memory. "
        "Supports optional query filters: `done` (true/false) and `search` (substring match on title)."
    ),
    tags=["Tasks"],
)
def list_tasks(done: Optional[bool] = None, search: Optional[str] = None):
    """
    List all tasks, with optional filters:

    - **done** — filter by completion status (`true` or `false`)
    - **search** — return only tasks whose title contains this substring (case-insensitive)
    """
    result = tasks
    if done is not None:
        result = [t for t in result if t["done"] == done]
    if search:
        result = [t for t in result if search.lower() in t["title"].lower()]
    return result


@app.get(
    "/tasks/{task_id}",
    response_model=TaskOut,
    summary="Get one task",
    description="Fetch a single task by its numeric ID. Returns 404 if not found.",
    tags=["Tasks"],
)
def get_task(task_id: int):
    """Return the task with the given **task_id**, or 404 if it doesn't exist."""
    return find_task(task_id)


# ──────────────────────────────────────────────
# Stage 3 — Create (POST /tasks)
# ──────────────────────────────────────────────

@app.post(
    "/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    description=(
        "Add a new task. Send `{\"title\": \"...\"}` in the body; "
        "`done` defaults to `false`. "
        "Returns the created task with its assigned ID and **201 Created**. "
        "Missing or empty title → **400 Bad Request**."
    ),
    tags=["Tasks"],
)
def create_task(body: TaskIn):
    """
    Create a new task.

    - **title** *(required)* — the task description; must not be empty
    - **done** *(optional, default false)* — mark as already completed
    """
    global next_id
    new_task = {"id": next_id, "title": body.title, "done": body.done}
    tasks.append(new_task)
    next_id += 1
    return new_task


# ──────────────────────────────────────────────
# Stage 4 — Update & Delete
# ──────────────────────────────────────────────

@app.put(
    "/tasks/{task_id}",
    response_model=TaskOut,
    summary="Update a task",
    description=(
        "Replace a task's `title` and/or `done` flag. "
        "Returns the updated task. "
        "Unknown ID → **404**. Empty/missing title → **400**."
    ),
    tags=["Tasks"],
)
def update_task(task_id: int, body: TaskIn):
    """
    Update an existing task.

    - **task_id** — ID of the task to change
    - **title** *(required)* — new title; must not be empty
    - **done** *(optional)* — new completion status
    """
    task = find_task(task_id)
    task["title"] = body.title
    task["done"] = body.done
    return task


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description=(
        "Remove a task permanently (from memory). "
        "Returns **204 No Content** on success — nothing in the body. "
        "Unknown ID → **404**."
    ),
    tags=["Tasks"],
)
def delete_task(task_id: int):
    """Delete the task with the given **task_id**. Returns 204 with no body on success."""
    task = find_task(task_id)
    tasks.remove(task)


# ──────────────────────────────────────────────
# Extras — Stats & Reset
# ──────────────────────────────────────────────

@app.get(
    "/stats",
    summary="Task statistics",
    description="Returns a quick summary: total tasks, how many are done, and how many are still open.",
    tags=["Extras"],
)
def stats():
    """Return task counts: total, done, and open."""
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    return {
        "total": total,
        "done": done_count,
        "open": total - done_count,
    }


@app.post(
    "/reset",
    summary="Reset to seed data",
    description=(
        "Wipe all tasks and restore the original 3 seed tasks. "
        "Useful for demos. Illustrates why in-memory data is volatile."
    ),
    tags=["Extras"],
    status_code=status.HTTP_200_OK,
)
def reset():
    """Restore the 3 seed tasks and reset the ID counter."""
    global tasks, next_id
    tasks = copy.deepcopy(SEED_TASKS)
    next_id = 4
    return {"message": "Tasks reset to seed data", "tasks": tasks}
