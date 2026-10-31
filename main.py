"""
Task API — FlyRank W2 · A1
Stage 2: Read endpoints with 404
"""

from fastapi import FastAPI, HTTPException, status

app = FastAPI(title="Task API")

# In-memory "database"
tasks = [
    {"id": 1, "title": "Read the FastAPI docs", "done": True},
    {"id": 2, "title": "Build the CRUD API",    "done": False},
    {"id": 3, "title": "Push to GitHub",         "done": False},
]


@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )
