"""Simulation orchestration for single and batch requests."""

from __future__ import annotations

from typing import Any, Iterable

from ..config import WALL_LOCATIONS_M, WALL_OPENING_HEIGHTS_M
from ..models.analytical_model import run_no_wall_baseline, run_simulation
from ..schemas import BatchCase, SimulationError, SimulationRequest


def make_case_id(L_w_m: float, h_w_m: float) -> str:
    return f"L{int(round(L_w_m)):03d}_H{int(round(h_w_m)):02d}"


def default_batch_requests(
    correction_mode: str = "pool_carrera_flux",
    *,
    include_profiles: bool = False,
) -> list[SimulationRequest]:
    """Deterministic 16-case Cartesian product from the paper."""

    return [
        SimulationRequest(
            L_w_m=float(L_w),
            h_w_m=float(h_w),
            correction_mode=correction_mode,  # type: ignore[arg-type]
            include_profiles=include_profiles,
            case_id=make_case_id(L_w, h_w),
        )
        for L_w in WALL_LOCATIONS_M
        for h_w in WALL_OPENING_HEIGHTS_M
    ]


def run_single(request: SimulationRequest) -> dict[str, Any]:
    parameters = request.to_parameters()
    if request.mode == "no_wall":
        result = run_no_wall_baseline(
            case_id=request.case_id or "no_wall",
            include_profiles=request.include_profiles,
            parameters=parameters,
        )
    else:
        result = run_simulation(
            parameters,
            case_id=request.case_id or make_case_id(float(request.L_w_m), float(request.h_w_m)),
            include_profiles=request.include_profiles,
            profile_points=request.profile_points,
        )
    return result.as_dict()


def _summary_case(
    request: SimulationRequest,
    result: dict[str, Any] | None,
    error: Exception | None,
) -> BatchCase:
    case_id = request.case_id or (
        make_case_id(float(request.L_w_m), float(request.h_w_m))
        if request.L_w_m is not None and request.h_w_m is not None
        else "unknown"
    )
    if result is None:
        return BatchCase(
            case_id=case_id,
            L_w_m=request.L_w_m,
            h_w_m=request.h_w_m,
            status="failed",
            error=SimulationError(
                case_id=case_id,
                code=type(error).__name__ if error else "MODEL_ERROR",
                message=str(error) if error else "unknown model error",
            ),
        )
    return BatchCase(
        case_id=case_id,
        L_w_m=request.L_w_m,
        h_w_m=request.h_w_m,
        scenario_id=result["scenario_id"],
        scenario_title=result["scenario_title"],
        toe_location_x_t_m=result["toe_location_x_t_m"],
        toe_location_uncorrected_m=result["toe_location_uncorrected_m"],
        xh_m=result["xh_m"],
        status="success",
        warnings=result.get("warnings", []),
    )


def run_batch(
    requests: Iterable[SimulationRequest],
    *,
    include_profiles: bool = False,
) -> dict[str, Any]:
    """Run each case independently; one failure never corrupts the others."""

    cases: list[BatchCase] = []
    successes = 0
    failures = 0
    for request in requests:
        request = request.model_copy(update={"include_profiles": include_profiles})
        try:
            result = run_single(request)
        except Exception as exc:  # deliberately per-case isolation
            failures += 1
            cases.append(_summary_case(request, None, exc))
            continue
        successes += 1
        cases.append(_summary_case(request, result, None))

    status = "success" if failures == 0 else ("partial" if successes else "failed")
    return {
        "status": status,
        "total": len(cases),
        "successful": successes,
        "failed": failures,
        "cases": [case.model_dump() for case in cases],
        "metadata": {
            "include_profiles": include_profiles,
            "ordering": "L_w ascending, then h_w ascending",
        },
    }
