from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse

settings = get_settings()

app = FastAPI(title="Pulsar API", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Technical liveness check only."""
    return HealthResponse(status="ok", service="pulsar-api", demo_mode=settings.demo_mode)


@app.post(
    "/analyze",
    status_code=501,
    responses={200: {"model": AnalyzeResponse}, 501: {"description": "Not implemented"}},
)
def analyze(_request: AnalyzeRequest) -> JSONResponse:
    """Planned endpoint (see docs/api-contract.md). Intentionally unimplemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "POST /analyze is not implemented yet."},
    )
