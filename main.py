"""
Task API — FlyRank W3 · A1
Stage 0: Create SQLite database (tasks.db)
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, field_validator
from typing import Optional
from pathlib import Path
import sqlite3

app = FastAPI(
    title="Task API",
    description="A CRUD API for managing tasks backed by SQLite (tasks.db).",
    version="2.0",
)

DB_PATH = Path(__file__).parent / "tasks.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    # Seed with 3 example tasks ONLY if table is empty
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
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


# Initialize database on module load
init_db()


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "2.0",
        "storage": "SQLite (tasks.db)",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def health():
    return {"status": "ok", "database": "connected"}
