"""Data access for /analyze. Server-side only: uses SUPABASE_SECRET_KEY, which bypasses RLS,
so every query here filters by profile explicitly. Tests swap in a fake via FastAPI
dependency overrides and never touch the network."""

from datetime import datetime
from functools import cached_property
from typing import Any, Protocol

from app.config import Settings
from app.errors import ServiceUnavailable
from app.ml import AnalysisResult, Checkin

CHECKIN_COLUMNS = "id, recorded_at, sleep_duration_hours, resting_heart_rate, mood_rating"


class AnalysisRepository(Protocol):
    def profile_owned_by(self, profile_id: str, user_id: str) -> bool: ...

    def get_checkin(self, profile_id: str, checkin_id: str) -> Checkin | None: ...

    def latest_checkin(self, profile_id: str) -> Checkin | None: ...

    def checkins_before(self, profile_id: str, before: datetime, limit: int) -> list[Checkin]:
        """Up to `limit` check-ins recorded before `before`, oldest first."""
        ...

    def save_result(self, profile_id: str, result: AnalysisResult) -> None:
        """Store the result, replacing any earlier row for the same profile, check-in
        (or no check-in) and model version."""
        ...


def _num(value: Any) -> float | None:
    return None if value is None else float(value)


def checkin_from_row(row: dict[str, Any]) -> Checkin:
    return Checkin(
        id=row["id"],
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
        sleep_duration_hours=_num(row["sleep_duration_hours"]),
        resting_heart_rate=_num(row["resting_heart_rate"]),
        mood_rating=_num(row["mood_rating"]),
    )


def result_row(profile_id: str, result: AnalysisResult) -> dict[str, Any]:
    return {
        "profile_id": profile_id,
        "checkin_id": result.checkin_id,
        "score": result.score,
        "review_label": result.label,
        "explanation": result.details,
        "model_version": result.model_version,
    }


class SupabaseRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @cached_property
    def _client(self):
        if not (self._settings.supabase_url and self._settings.supabase_secret_key):
            raise ServiceUnavailable("SUPABASE_URL and SUPABASE_SECRET_KEY must be set.")
        from supabase import create_client

        return create_client(self._settings.supabase_url, self._settings.supabase_secret_key)

    def _run(self, query):
        try:
            return query.execute().data
        except ServiceUnavailable:
            raise
        except Exception as exc:  # network or PostgREST error
            raise ServiceUnavailable("Database request failed.") from exc

    def profile_owned_by(self, profile_id: str, user_id: str) -> bool:
        rows = self._run(
            self._client.table("crew_profiles")
            .select("id")
            .eq("id", profile_id)
            .eq("user_id", user_id)
            .limit(1)
        )
        return bool(rows)

    def get_checkin(self, profile_id: str, checkin_id: str) -> Checkin | None:
        rows = self._run(
            self._client.table("health_checkins")
            .select(CHECKIN_COLUMNS)
            .eq("profile_id", profile_id)
            .eq("id", checkin_id)
            .limit(1)
        )
        return checkin_from_row(rows[0]) if rows else None

    def latest_checkin(self, profile_id: str) -> Checkin | None:
        rows = self._run(
            self._client.table("health_checkins")
            .select(CHECKIN_COLUMNS)
            .eq("profile_id", profile_id)
            .order("recorded_at", desc=True)
            .limit(1)
        )
        return checkin_from_row(rows[0]) if rows else None

    def checkins_before(self, profile_id: str, before: datetime, limit: int) -> list[Checkin]:
        rows = self._run(
            self._client.table("health_checkins")
            .select(CHECKIN_COLUMNS)
            .eq("profile_id", profile_id)
            .lt("recorded_at", before.isoformat())
            .order("recorded_at", desc=True)
            .limit(limit)
        )
        return [checkin_from_row(r) for r in reversed(rows)]

    def save_result(self, profile_id: str, result: AnalysisResult) -> None:
        delete = (
            self._client.table("anomaly_results")
            .delete()
            .eq("profile_id", profile_id)
            .eq("model_version", result.model_version)
        )
        delete = (
            delete.eq("checkin_id", result.checkin_id)
            if result.checkin_id
            else delete.is_("checkin_id", "null")
        )
        self._run(delete)
        self._run(self._client.table("anomaly_results").insert(result_row(profile_id, result)))
