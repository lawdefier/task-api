"""
Service Layer: Implements business logic and orchestrates data access via TaskRepository.
This layer is 100% agnostic to whether data is stored in memory, SQLite, or PostgreSQL.
"""

from typing import Optional
from repository import TaskRepository


class TaskService:
    """Core domain logic for task operations."""

    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def list_tasks(
        self,
        done: Optional[bool] = None,
        search: Optional[str] = None,
        sort: Optional[str] = "id",
    ) -> list[dict]:
        return self.repository.list_tasks(done=done, search=search, sort=sort)

    def get_task(self, task_id: int) -> Optional[dict]:
        return self.repository.get_by_id(task_id)

    def create_task(self, title: str, done: bool = False) -> dict:
        return self.repository.create_task(title=title, done=done)

    def update_task(self, task_id: int, title: str, done: bool) -> Optional[dict]:
        return self.repository.update_task(task_id=task_id, title=title, done=done)

    def delete_task(self, task_id: int) -> bool:
        return self.repository.delete_task(task_id=task_id)

    def get_stats(self) -> dict:
        return self.repository.get_stats()

    def reset_database(self) -> None:
        self.repository.reset()

    def is_healthy(self) -> bool:
        return self.repository.check_health()
