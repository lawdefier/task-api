"""
Task API — FlyRank W3 · A1
A full CRUD API for managing tasks backed by a persistent SQLite database (tasks.db).
Data survives server restarts.
"""

from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, field_validator
from typing import Optional
from pathlib import Path
import sqlite3

# ──────────────────────────────────────────────
# App configuration
# ──────────────────────────────────────────────

app = FastAPI(
    title="Task API",
    description=(
        "A persistent to-do list CRUD API built for FlyRank Week 3 Assignment 1. "
        "Backed by SQLite (`tasks.db`). Data survives server restarts."
    ),
    version="2.0",
)

DB_PATH = Path(__file__).parent / "tasks.db"


# ──────────────────────────────────────────────
# Database connection and initialization
# ──────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    """Return a connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Ensure the tasks table exists.
    If the table is empty (first run), insert the 3 default example tasks.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Read the FastAPI docs", 1),
                ("Build the CRUD API", 0),
                ("Push to GitHub", 0),
            ],
        )
    conn.commit()
    conn.close()


# Ensure database is created immediately upon module load & on app startup
init_db()


@app.on_event("startup")
def startup_event():
    init_db()


# ──────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────

class TaskIn(BaseModel):
    """Payload for creating or updating a task."""
    title: str
    done: Optional[bool] = False

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()


class TaskOut(BaseModel):
    """Representation of a task returned by the API."""
    id: int
    title: str
    done: bool


# ──────────────────────────────────────────────
# Meta endpoints
# ──────────────────────────────────────────────

@app.get(
    "/",
    summary="API Info",
    description="Returns metadata about the API and available endpoints.",
    tags=["Meta"],
)
def root():
    return {
        "name": "Task API",
        "version": "2.0",
        "storage": "SQLite (tasks.db)",
        "endpoints": ["/tasks", "/tasks/{id}", "/stats", "/reset", "/health"],
    }


@app.get(
    "/health",
    summary="Health check",
    description="Verifies the server and SQLite database connection are alive.",
    tags=["Meta"],
)
def health():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {e}",
        )


# ──────────────────────────────────────────────
# CRUD Endpoints
# ──────────────────────────────────────────────

@app.get(
    "/tasks",
    response_model=list[TaskOut],
    summary="List all tasks",
    description=(
        "Retrieves tasks from SQLite. Supports optional filtering by `done` "
        "status and keyword substring matching on `title` via SQL `LIKE`."
    ),
    tags=["Tasks"],
)
def list_tasks(
    done: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search keyword in task title (SQL LIKE)"),
    sort: Optional[str] = Query("id", description="Sort field: 'id' or 'title'"),
):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT id, title, done FROM tasks WHERE 1=1"
    params = []

    if done is not None:
        query += " AND done = ?"
        params.append(1 if done else 0)

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    if sort == "title":
        query += " ORDER BY title ASC"
    else:
        query += " ORDER BY id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in rows]


@app.get(
    "/tasks/{task_id}",
    response_model=TaskOut,
    summary="Get single task",
    description="Fetches a single task by its integer primary key from SQLite. Returns 404 if not found.",
    tags=["Tasks"],
)
def get_task(task_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.post(
    "/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Inserts a new task row into SQLite. Returns 201 Created.",
    tags=["Tasks"],
)
def create_task(body: TaskIn):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (body.title, 1 if body.done else 0),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"id": new_id, "title": body.title, "done": bool(body.done)}


@app.put(
    "/tasks/{task_id}",
    response_model=TaskOut,
    summary="Update a task",
    description="Updates title and/or done status for the specified task in SQLite.",
    tags=["Tasks"],
)
def update_task(task_id: int, body: TaskIn):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    cursor.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (body.title, 1 if body.done else 0, task_id),
    )
    conn.commit()
    conn.close()

    return {"id": task_id, "title": body.title, "done": bool(body.done)}


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Deletes a task row from SQLite by ID. Returns 204 No Content.",
    tags=["Tasks"],
)
def delete_task(task_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return None


# ──────────────────────────────────────────────
# Extras: Stats & Reset
# ──────────────────────────────────────────────

@app.get(
    "/stats",
    summary="Task statistics",
    description="Computes total, completed, and open task counts using SQL `COUNT()` aggregations.",
    tags=["Extras"],
)
def get_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tasks")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE done = 1")
    done_count = cursor.fetchone()[0]

    conn.close()
    return {
        "total": total,
        "done": done_count,
        "open": total - done_count,
    }


@app.post(
    "/reset",
    summary="Reset database",
    description="Wipes all tasks and re-inserts the 3 initial seed tasks into SQLite.",
    tags=["Extras"],
)
def reset_database():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks")
    try:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='tasks'")
    except sqlite3.OperationalError:
        pass

    cursor.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [
            ("Read the FastAPI docs", 1),
            ("Build the CRUD API", 0),
            ("Push to GitHub", 0),
        ],
    )
    conn.commit()
    conn.close()
    return {"message": "Database reset to the 3 initial seed tasks"}
