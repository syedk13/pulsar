"""POST /analyze with a fake repository and fake auth (no network)."""

from dataclasses import replace
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.errors import ServiceUnavailable
from app.main import app, get_auth_verifier, get_repository
from app.ml import MODEL_VERSION, AnalysisResult, Checkin
from app.repository import result_row
from app.schemas import AnalyzeResponse
from tests.conftest import steady

USER_A, USER_B = "user-a", "user-b"
PROFILE_A, PROFILE_B, PROFILE_EMPTY = str(uuid4()), str(uuid4()), str(uuid4())


class FakeAuth:
    tokens = {"token-a": USER_A, "token-b": USER_B}

    def user_id(self, access_token: str) -> str | None:
        return self.tokens.get(access_token)


class FakeRepository:
    def __init__(self) -> None:
        self.owners = {PROFILE_A: USER_A, PROFILE_B: USER_B, PROFILE_EMPTY: USER_A}
        self.checkins: dict[str, list[Checkin]] = {
            PROFILE_A: [replace(c, id=str(uuid4())) for c in steady(20)],
            PROFILE_B: [Checkin(str(uuid4()), c.recorded_at, 6.5, 60, 4) for c in steady(10)],
            PROFILE_EMPTY: [],
        }
        self.results: list[dict] = []
        self.calls: list[tuple] = []

    def profile_owned_by(self, profile_id: str, user_id: str) -> bool:
        return self.owners.get(profile_id) == user_id

    def get_checkin(self, profile_id: str, checkin_id: str) -> Checkin | None:
        return next((c for c in self.checkins.get(profile_id, []) if c.id == checkin_id), None)

    def latest_checkin(self, profile_id: str) -> Checkin | None:
        rows = self.checkins.get(profile_id, [])
        return max(rows, key=lambda c: c.recorded_at) if rows else None

    def checkins_before(self, profile_id: str, before: datetime, limit: int) -> list[Checkin]:
        self.calls.append(("before", profile_id, before, limit))
        rows = sorted(
            (c for c in self.checkins.get(profile_id, []) if c.recorded_at < before),
            key=lambda c: c.recorded_at,
        )
        return rows[-limit:]

    def save_result(self, profile_id: str, result: AnalysisResult) -> None:
        # Same replace-semantics as SupabaseRepository: one row per (profile, check-in, model).
        self.results = [
            r
            for r in self.results
            if (r["profile_id"], r["checkin_id"], r["model_version"])
            != (profile_id, result.checkin_id, result.model_version)
        ]
        self.results.append(result_row(profile_id, result))


@pytest.fixture
def repo():
    fake = FakeRepository()
    app.dependency_overrides[get_repository] = lambda: fake
    app.dependency_overrides[get_auth_verifier] = lambda: FakeAuth()
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client(repo):
    return TestClient(app)


def post(client, body, token: str | None = "token-a"):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/analyze", json=body, headers=headers)


def test_missing_token_is_401(client, repo):
    r = post(client, {"profile_id": PROFILE_A}, token=None)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert repo.results == []


def test_missing_token_is_401_even_without_a_body(client):
    assert client.post("/analyze").status_code == 401


def test_invalid_token_is_401(client):
    assert post(client, {"profile_id": PROFILE_A}, token="forged").status_code == 401


def test_other_users_profile_is_404(client, repo):
    r = post(client, {"profile_id": PROFILE_B})  # user A asking about B's profile
    assert r.status_code == 404
    assert r.json()["detail"] == "Profile or check-in not found."
    assert repo.results == []


def test_unknown_profile_is_same_404(client):
    r = post(client, {"profile_id": str(uuid4())})
    assert r.status_code == 404
    assert r.json()["detail"] == "Profile or check-in not found."


def test_checkin_from_another_profile_is_404(client, repo):
    other = repo.checkins[PROFILE_B][0].id
    r = post(client, {"profile_id": PROFILE_A, "checkin_id": other})
    assert r.status_code == 404


def test_null_checkin_id_analyses_the_latest(client, repo):
    latest = repo.checkins[PROFILE_A][-1]
    r = post(client, {"profile_id": PROFILE_A, "checkin_id": None})
    assert r.status_code == 200
    body = AnalyzeResponse.model_validate(r.json())
    assert str(body.checkin_id) == latest.id
    assert body.label in ("within_baseline", "worth_reviewing")
    assert body.score is not None
    assert body.model_version == MODEL_VERSION
    # Only check-ins before the scored one, at most 14, are loaded.
    assert repo.calls[-1] == ("before", PROFILE_A, latest.recorded_at, 14)


def test_explicit_checkin_uses_history_before_it(client, repo):
    early = repo.checkins[PROFILE_A][3]  # only 3 earlier check-ins
    r = post(client, {"profile_id": PROFILE_A, "checkin_id": early.id})
    body = AnalyzeResponse.model_validate(r.json())
    assert str(body.checkin_id) == early.id
    assert body.label == "insufficient_data"
    assert body.score is None
    assert "3 earlier check-ins" in body.explanation


def test_result_is_written_and_reanalysis_replaces_it(client, repo):
    first = post(client, {"profile_id": PROFILE_A}).json()
    second = post(client, {"profile_id": PROFILE_A}).json()
    assert first == second
    assert len(repo.results) == 1
    row = repo.results[0]
    assert row["profile_id"] == PROFILE_A
    assert row["checkin_id"] == first["checkin_id"]
    assert row["review_label"] == first["label"]
    assert row["score"] == first["score"]
    assert row["model_version"] == MODEL_VERSION
    assert row["explanation"]["text"] == first["explanation"]
    assert row["explanation"]["window"]["baseline_checkins"] == 14
    assert "contributing_changes" in row["explanation"]


def test_profile_without_checkins_is_insufficient_data_and_saved(client, repo):
    r = post(client, {"profile_id": PROFILE_EMPTY})
    assert r.status_code == 200
    body = AnalyzeResponse.model_validate(r.json())
    assert body.label == "insufficient_data"
    assert body.checkin_id is None and body.score is None
    assert body.contributing_changes == []
    assert "no check-ins yet" in body.explanation
    post(client, {"profile_id": PROFILE_EMPTY})
    saved = [r for r in repo.results if r["profile_id"] == PROFILE_EMPTY]
    assert len(saved) == 1 and saved[0]["checkin_id"] is None
    assert saved[0]["review_label"] == "insufficient_data"


def test_bad_body_with_valid_token_is_422(client):
    assert post(client, {"profile_id": "not-a-uuid"}).status_code == 422


def test_supabase_unavailable_is_503(client, repo):
    def boom(*_args):
        raise ServiceUnavailable("Database request failed.")

    repo.profile_owned_by = boom
    r = post(client, {"profile_id": PROFILE_A})
    assert r.status_code == 503
    assert r.json() == {"detail": "Database request failed."}
