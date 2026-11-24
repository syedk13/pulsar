from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import AuthVerifier, SupabaseAuthVerifier
from app.config import get_settings
from app.errors import ServiceUnavailable
from app.ml import AnalysisResult, analyze_checkin
from app.ml.features import BASELINE_WINDOW
from app.repository import AnalysisRepository, SupabaseRepository
from app.schemas import AnalyzeRequest, AnalyzeResponse, ContributingChange, HealthResponse

settings = get_settings()

app = FastAPI(title="Pulsar API", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

bearer = HTTPBearer(auto_error=False, description="Supabase access token of the signed-in user")
_repository = SupabaseRepository(settings)
_verifier = SupabaseAuthVerifier(settings)

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Profile or check-in not found.")


@app.exception_handler(ServiceUnavailable)
def service_unavailable(_request: Request, exc: ServiceUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def get_repository() -> AnalysisRepository:
    return _repository


def get_auth_verifier() -> AuthVerifier:
    return _verifier


def current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    verifier: Annotated[AuthVerifier, Depends(get_auth_verifier)],
) -> str:
    """401 unless the request carries a valid Supabase access token."""
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "A valid Supabase access token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or not credentials.credentials:
        raise unauthorized
    user_id = verifier.user_id(credentials.credentials)
    if not user_id:
        raise unauthorized
    return user_id


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Technical liveness check only."""
    return HealthResponse(status="ok", service="pulsar-api", demo_mode=settings.demo_mode)


def to_response(result: AnalysisResult) -> AnalyzeResponse:
    return AnalyzeResponse(
        checkin_id=result.checkin_id,
        score=result.score,
        label=result.label,
        explanation=result.explanation,
        contributing_changes=[
            ContributingChange(**c.__dict__) for c in result.contributing_changes
        ],
        model_version=result.model_version,
    )


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        401: {"description": "Missing or invalid access token"},
        404: {"description": "Profile not found or not yours, or check-in not in that profile"},
        503: {"description": "Supabase not configured or unreachable"},
    },
)
def analyze(
    body: AnalyzeRequest,
    user_id: Annotated[str, Depends(current_user_id)],
    repo: Annotated[AnalysisRepository, Depends(get_repository)],
) -> AnalyzeResponse:
    """Compare a check-in with the profile's personal baseline and store the result.

    Decision support only: compares the person with their own recent history.
    """
    profile_id = str(body.profile_id)
    if not repo.profile_owned_by(profile_id, user_id):
        raise NOT_FOUND  # same answer for unknown and not-owned profiles
    if body.checkin_id is not None:
        target = repo.get_checkin(profile_id, str(body.checkin_id))
        if target is None:
            raise NOT_FOUND
    else:
        target = repo.latest_checkin(profile_id)

    earlier = (
        []
        if target is None
        else repo.checkins_before(profile_id, target.recorded_at, BASELINE_WINDOW)
    )
    result = analyze_checkin(target, earlier)
    repo.save_result(profile_id, result)
    return to_response(result)
