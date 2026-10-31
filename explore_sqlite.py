"""
FlyRank W3 · A1 — Stage 4: Learn your first SQL
Script demonstrating manual SQL queries executed against tasks.db
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"

def run_query(title, sql, params=()):
    print(f"\n{'=' * 60}")
    print(f"QUERY: {title}")
    print(f"SQL:   {sql}")
    print(f"{'=' * 60}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, params)
    
    if sql.strip().upper().startswith("SELECT"):
        rows = cursor.fetchall()
        if not rows:
            print("(0 rows returned)")
        else:
            col_names = [d[0] for d in cursor.description]
            header = " | ".join(f"{c:<12}" for c in col_names)
            print(header)
            print("-" * len(header))
            for row in rows:
                print(" | ".join(f"{str(row[c]):<12}" for c in col_names))
    else:
        conn.commit()
        print(f"Rows affected: {cursor.rowcount}")
    
    conn.close()

if __name__ == "__main__":
    # Ensure fresh DB with initial tasks
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    c.execute("DELETE FROM tasks")
    c.execute("DELETE FROM sqlite_sequence WHERE name='tasks'")
    c.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [
            ("Read the FastAPI docs", 1),
            ("Build the CRUD API", 0),
            ("Push to GitHub", 0),
        ],
    )
    conn.commit()
    conn.close()

    print("Running Stage 4 SQL exploration queries on tasks.db:")

    # 1. List every task
    run_query("1. List every task", "SELECT * FROM tasks;")

    # 2. Show only completed tasks
    run_query("2. Show only completed tasks", "SELECT * FROM tasks WHERE done = 1;")

    # 3. Count all tasks
    run_query("3. Count all tasks", "SELECT COUNT(*) AS total_tasks FROM tasks;")

    # 4. Mark every task as completed
    run_query("4. Mark every task as completed", "UPDATE tasks SET done = 1;")
    run_query("   Verify all completed", "SELECT * FROM tasks;")

    # 5. Delete all completed tasks
    run_query("5. Delete all completed tasks", "DELETE FROM tasks WHERE done = 1;")
    run_query("   Verify after delete", "SELECT * FROM tasks;")

    # Re-seed for server use
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        [
            ("Read the FastAPI docs", 1),
            ("Build the CRUD API", 0),
            ("Push to GitHub", 0),
        ],
    )
    conn.commit()
    conn.close()
    print("\n[OK] Database re-seeded with 3 baseline tasks for API operation.")

