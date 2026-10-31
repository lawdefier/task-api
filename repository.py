"""
Repository Layer: Defines the TaskRepository interface and concrete implementations:
- InMemoryTaskRepository (Week 2 baseline)
- PostgresTaskRepository (Week 3 Assignment 2 - Primary)
- SQLiteTaskRepository (Local fallback if Postgres container is offline)
"""

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3


class TaskRepository(ABC):
    """Abstract Interface for Task Storage."""

    @abstractmethod
    def list_tasks(
        self,
        done: Optional[bool] = None,
        search: Optional[str] = None,
        sort: Optional[str] = "id",
    ) -> list[dict]:
        pass

    @abstractmethod
    def get_by_id(self, task_id: int) -> Optional[dict]:
        pass

    @abstractmethod
    def create_task(self, title: str, done: bool = False) -> dict:
        pass

    @abstractmethod
    def update_task(self, task_id: int, title: str, done: bool) -> Optional[dict]:
        pass

    @abstractmethod
    def delete_task(self, task_id: int) -> bool:
        pass

    @abstractmethod
    def get_stats(self) -> dict:
        pass

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def check_health(self) -> bool:
        pass


# ──────────────────────────────────────────────
# 1. InMemory Repository (A1 Legacy)
# ──────────────────────────────────────────────

class InMemoryTaskRepository(TaskRepository):
    """In-memory array implementation from Week 2."""

    def __init__(self):
        self.tasks: list[dict] = [
            {"id": 1, "title": "Read the FastAPI docs", "done": True},
            {"id": 2, "title": "Build the CRUD API",    "done": False},
            {"id": 3, "title": "Push to GitHub",         "done": False},
        ]
        self.next_id: int = 4

    def list_tasks(self, done: Optional[bool] = None, search: Optional[str] = None, sort: Optional[str] = "id") -> list[dict]:
        res = list(self.tasks)
        if done is not None:
            res = [t for t in res if t["done"] == done]
        if search:
            res = [t for t in res if search.lower() in t["title"].lower()]
        if sort == "title":
            res.sort(key=lambda x: x["title"].lower())
        else:
            res.sort(key=lambda x: x["id"])
        return res

    def get_by_id(self, task_id: int) -> Optional[dict]:
        for t in self.tasks:
            if t["id"] == task_id:
                return t
        return None

    def create_task(self, title: str, done: bool = False) -> dict:
        task = {"id": self.next_id, "title": title, "done": done}
        self.tasks.append(task)
        self.next_id += 1
        return task

    def update_task(self, task_id: int, title: str, done: bool) -> Optional[dict]:
        task = self.get_by_id(task_id)
        if not task:
            return None
        task["title"] = title
        task["done"] = done
        return task

    def delete_task(self, task_id: int) -> bool:
        task = self.get_by_id(task_id)
        if not task:
            return False
        self.tasks.remove(task)
        return True

    def get_stats(self) -> dict:
        total = len(self.tasks)
        done_count = sum(1 for t in self.tasks if t["done"])
        return {"total": total, "done": done_count, "open": total - done_count}

    def reset(self) -> None:
        self.tasks = [
            {"id": 1, "title": "Read the FastAPI docs", "done": True},
            {"id": 2, "title": "Build the CRUD API",    "done": False},
            {"id": 3, "title": "Push to GitHub",         "done": False},
        ]
        self.next_id = 4

    def check_health(self) -> bool:
        return True


# ──────────────────────────────────────────────
# 2. PostgreSQL Repository (W3 · A2 Production)
# ──────────────────────────────────────────────

class PostgresTaskRepository(TaskRepository):
    """Production Repository backed by PostgreSQL in Docker."""

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(self.connection_url, cursor_factory=RealDictCursor, connect_timeout=1)

    def _init_db(self):
        """Create table and initial seeds if not exists."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            id SERIAL PRIMARY KEY,
                            title VARCHAR(255) NOT NULL,
                            done BOOLEAN NOT NULL DEFAULT FALSE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
                    """)
                    cur.execute("SELECT COUNT(*) AS count FROM tasks")
                    row = cur.fetchone()
                    if row and row["count"] == 0:
                        cur.executemany(
                            "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                            [
                                ("Read the FastAPI docs", True),
                                ("Build the CRUD API", False),
                                ("Push to GitHub", False),
                            ],
                        )
                conn.commit()
        except Exception as e:
            # Table initialization error will be caught when database is online
            pass

    def list_tasks(self, done: Optional[bool] = None, search: Optional[str] = None, sort: Optional[str] = "id") -> list[dict]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                query = "SELECT id, title, done FROM tasks WHERE 1=1"
                params = []
                if done is not None:
                    query += " AND done = %s"
                    params.append(done)
                if search:
                    query += " AND title ILIKE %s"
                    params.append(f"%{search}%")
                if sort == "title":
                    query += " ORDER BY title ASC"
                else:
                    query += " ORDER BY id ASC"
                cur.execute(query, params)
                return [dict(r) for r in cur.fetchall()]

    def get_by_id(self, task_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def create_task(self, title: str, done: bool = False) -> dict:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
                    (title, done),
                )
                row = cur.fetchone()
                conn.commit()
                return dict(row)

    def update_task(self, task_id: int, title: str, done: bool) -> Optional[dict]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tasks SET title = %s, done = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING id, title, done",
                    (title, done, task_id),
                )
                row = cur.fetchone()
                conn.commit()
                return dict(row) if row else None

    def delete_task(self, task_id: int) -> bool:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
                conn.commit()
                return cur.rowcount > 0

    def get_stats(self) -> dict:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS total FROM tasks")
                total = cur.fetchone()["total"]
                cur.execute("SELECT COUNT(*) AS done FROM tasks WHERE done = TRUE")
                done_count = cur.fetchone()["done"]
                return {"total": total, "done": done_count, "open": total - done_count}

    def reset(self) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE tasks RESTART IDENTITY")
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    [
                        ("Read the FastAPI docs", True),
                        ("Build the CRUD API", False),
                        ("Push to GitHub", False),
                    ],
                )
            conn.commit()

    def check_health(self) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False


# ──────────────────────────────────────────────
# 3. SQLite Repository (Fallback when Docker is stopped)
# ──────────────────────────────────────────────

class SQLiteTaskRepository(TaskRepository):
    """SQLite implementation when Postgres container is not active."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT 0
                )
            """)
            cur.execute("SELECT COUNT(*) FROM tasks")
            if cur.fetchone()[0] == 0:
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (?, ?)",
                    [
                        ("Read the FastAPI docs", 1),
                        ("Build the CRUD API", 0),
                        ("Push to GitHub", 0),
                    ],
                )
            conn.commit()

    def list_tasks(self, done: Optional[bool] = None, search: Optional[str] = None, sort: Optional[str] = "id") -> list[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
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
            cur.execute(query, params)
            return [{"id": r["id"], "title": r["title"], "done": bool(r["done"])} for r in cur.fetchall()]

    def get_by_id(self, task_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            return {"id": row["id"], "title": row["title"], "done": bool(row["done"])} if row else None

    def create_task(self, title: str, done: bool = False) -> dict:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title, 1 if done else 0))
            new_id = cur.lastrowid
            conn.commit()
            return {"id": new_id, "title": title, "done": done}

    def update_task(self, task_id: int, title: str, done: bool) -> Optional[dict]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
            if not cur.fetchone():
                return None
            cur.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (title, 1 if done else 0, task_id))
            conn.commit()
            return {"id": task_id, "title": title, "done": done}

    def delete_task(self, task_id: int) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
            if not cur.fetchone():
                return False
            cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return True

    def get_stats(self) -> dict:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tasks")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM tasks WHERE done = 1")
            done_count = cur.fetchone()[0]
            return {"total": total, "done": done_count, "open": total - done_count}

    def reset(self) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks")
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name='tasks'")
            except Exception:
                pass
            cur.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Read the FastAPI docs", 1),
                    ("Build the CRUD API", 0),
                    ("Push to GitHub", 0),
                ],
            )
            conn.commit()

    def check_health(self) -> bool:
        return True
