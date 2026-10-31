"""
Task API — FlyRank W2 · A1
Stage 4: Full CRUD (Update & Delete)
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, field_validator
from typing import Optional

app = FastAPI(title="Task API")

tasks = [
    {"id": 1, "title": "Read the FastAPI docs", "done": True},
    {"id": 2, "title": "Build the CRUD API",    "done": False},
    {"id": 3, "title": "Push to GitHub",         "done": False},
]
next_id = 4


class TaskIn(BaseModel):
    title: str
    done: Optional[bool] = False

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool


def find_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )


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


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int):
    return find_task(task_id)


@app.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskIn):
    global next_id
    new_task = {"id": next_id, "title": body.title, "done": body.done}
    tasks.append(new_task)
    next_id += 1
    return new_task


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskIn):
    task = find_task(task_id)
    task["title"] = body.title
    task["done"] = body.done
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    task = find_task(task_id)
    tasks.remove(task)
