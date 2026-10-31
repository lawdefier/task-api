"""
Task API Checkpoint & Persistence Verification Suite
Tests all endpoints and confirms SQLite database persistence.
"""

import urllib.request
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "tasks.db"
BASE_URL = "http://localhost:8000"


def req(method, url, data=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(
        url, data=body, method=method,
        headers={"Content-Type": "application/json"} if body else {}
    )
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, resp.read().decode()
    except Exception as e:
        return getattr(e, "code", "?"), getattr(e, "read", lambda: b"")().decode()


def test_api():
    print("=" * 65)
    print("RUNNING API CHECKPOINT TESTS")
    print("=" * 65)

    # 1. Reset database to guarantee known baseline
    req("POST", BASE_URL + "/reset")

    # 2. Get list of tasks
    status_tasks, body_tasks = req("GET", BASE_URL + "/tasks")
    tasks_list = json.loads(body_tasks) if status_tasks == 200 else []
    first_id = tasks_list[0]["id"] if tasks_list else 1
    second_id = tasks_list[1]["id"] if len(tasks_list) > 1 else 2

    checks = [
        ("GET",    "/",                    None,                                           200),
        ("GET",    "/health",              None,                                           200),
        ("GET",    "/tasks",               None,                                           200),
        ("GET",    f"/tasks/{first_id}",   None,                                           200),
        ("GET",    "/tasks/9999",          None,                                           404),
        ("POST",   "/tasks",               {"title": "Persistent Task from Test"},         201),
        ("POST",   "/tasks",               {},                                             422),
        ("PUT",    f"/tasks/{first_id}",   {"title": "FastAPI Docs Read", "done": True},  200),
        ("DELETE", f"/tasks/{second_id}",  None,                                           204),
        ("GET",    "/stats",               None,                                           200),
        ("GET",    "/tasks?search=Persist",None,                                           200),
        ("GET",    "/tasks?done=true",     None,                                           200),
    ]

    print(f"{'Method':<8} {'Path':<28} {'Expect':<8} {'Got':<8} Pass?")
    print("-" * 65)
    all_pass = True
    for method, path, data, expect in checks:
        status, body = req(method, BASE_URL + path, data)
        ok = (status == expect)
        if not ok:
            all_pass = False
        mark = "PASS" if ok else "FAIL"
        snippet = (body[:45].replace("\n", "") if body else "(empty)")
        print(f"{method:<8} {path:<28} {expect:<8} {status:<8} {mark}  {snippet}")

    # Persistence verification directly against SQLite database file
    print("\n" + "=" * 65)
    print("VERIFYING SQLITE DATABASE PERSISTENCE")
    print("=" * 65)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks WHERE title = ?", ("Persistent Task from Test",))
    persisted_task = cursor.fetchone()
    conn.close()

    if persisted_task:
        print(f"[PASS] Confirmed row in {DB_PATH.name}: ID={persisted_task[0]}, Title='{persisted_task[1]}'")
    else:
        print(f"[FAIL] Could not find row in {DB_PATH.name}")
        all_pass = False

    print("\n" + ("All checks passed successfully!" if all_pass else "SOME CHECKS FAILED."))
    return all_pass


if __name__ == "__main__":
    test_api()
