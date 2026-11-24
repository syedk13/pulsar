"""Request/response shapes for the API contract (see docs/api-contract.md).

Type definitions only — no validation logic beyond field types, no business logic.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    demo_mode: bool


class AnalyzeRequest(BaseModel):
    profile_id: UUID
    checkin_id: UUID | None = Field(default=None, description="null = the latest check-in")


class ContributingChange(BaseModel):
    feature: Literal["sleep_duration_hours", "resting_heart_rate", "mood_rating"]
    observed: float
    baseline: float = Field(description="Median of the baseline window")
    unit: str
    basis: Literal["this_checkin", "last_3_checkins"] = Field(
        description="Whether `observed` is this check-in's value or the average of the last 3"
    )


class AnalyzeResponse(BaseModel):
    checkin_id: UUID | None = Field(description="The check-in analysed; null if there is none")
    score: float | None = Field(description="Isolation Forest score in (0, 1); null if no score")
    label: Literal["within_baseline", "worth_reviewing", "insufficient_data"]
    explanation: str
    contributing_changes: list[ContributingChange]
    model_version: str
