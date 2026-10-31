"""
Pydantic Models and Data Structures for Task API
"""

from pydantic import BaseModel, field_validator
from typing import Optional


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
    """Shape of task returned by the API."""
    id: int
    title: str
    done: bool

    class Config:
        from_attributes = True
