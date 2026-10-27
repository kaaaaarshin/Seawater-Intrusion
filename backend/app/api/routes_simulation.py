"""Single and batch simulation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import (
    BatchRequest,
    BatchResponse,
    SimulationRequest,
    SimulationResponse,
)
from ..services.simulation_service import default_batch_requests, run_batch, run_single
from ..utils.errors import ApiError

router = APIRouter(prefix="/api", tags=["simulation"])


@router.post("/simulate", response_model=SimulationResponse)
def simulate(request: SimulationRequest) -> SimulationResponse:
    try:
        result = run_single(request)
    except (ValueError, RuntimeError) as exc:
        raise ApiError(
            "SIMULATION_INPUT_ERROR",
            str(exc),
            status_code=422,
        ) from exc
    return SimulationResponse(**result)


@router.post("/simulate/batch", response_model=BatchResponse)
def simulate_batch(request: BatchRequest) -> BatchResponse:
    if request.configurations is not None and len(request.configurations) == 0:
        raise ApiError(
            "EMPTY_BATCH",
            "configurations must contain at least one case",
            status_code=422,
            field="configurations",
        )
    configurations = request.configurations or default_batch_requests(
        correction_mode=request.correction_mode,
        include_profiles=request.include_profiles,
    )
    result = run_batch(
        configurations,
        include_profiles=request.include_profiles,
    )
    return BatchResponse(**result)
