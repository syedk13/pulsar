"""Request/response shapes for the planned API contract (see docs/api-contract.md).

Type definitions only — no validation logic beyond field types, no business logic.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    demo_mode: bool


class AnalyzeRequest(BaseModel):
    profile_id: UUID
    checkin_id: UUID | None = None


class ContributingChange(BaseModel):
    feature: str
    observed: float
    baseline: float
    unit: str


class AnalyzeResponse(BaseModel):
    score: float
    label: Literal["within_baseline", "worth_reviewing", "insufficient_data"]
    explanation: str
    contributing_changes: list[ContributingChange]
    model_version: str
