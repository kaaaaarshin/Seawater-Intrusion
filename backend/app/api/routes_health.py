"""Health and model-loading status."""

from __future__ import annotations

from fastapi import APIRouter

from ..config import APP_VERSION, MODEL_VERSION
from ..schemas import HealthResponse
from ..services.dataset_service import read_manifest

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    model_loaded = False
    model_error = ""
    try:
        from ..models.analytical_model import run_simulation  # noqa: F401

        model_loaded = True
    except Exception as exc:  # pragma: no cover - import diagnostics
        model_error = str(exc)

    manifest = read_manifest()
    validation_status = (
        (manifest or {}).get("validation_status", "not_run") or "not_run"
    )
    validated = validation_status == "passed"
    if model_loaded:
        message = "Backend is online and the analytical model module loaded."
        if model_error:
            message += f" Import warning: {model_error}"
    else:
        message = f"Backend is online but the analytical model failed to load: {model_error}"
        validation_status = "not_run"
        validated = False

    return HealthResponse(
        status="ok" if model_loaded else "degraded",
        app_version=APP_VERSION,
        model_version=MODEL_VERSION,
        model_loaded=model_loaded,
        validated=validated,
        validation_status=validation_status,
        message=message,
    )
