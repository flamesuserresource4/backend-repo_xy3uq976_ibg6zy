from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

# Each class corresponds to a Mongo collection: class name lowercased


class Project(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)


class Testcase(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Literal["Pass", "Fail", "Pending"] = "Pending"


class TestcaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[Literal["Pass", "Fail", "Pending"]] = None


class Plan(BaseModel):
    plan: Literal["free", "pro"] = "free"
