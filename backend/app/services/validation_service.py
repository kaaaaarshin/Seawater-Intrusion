"""Mathematical and paper-reference validation.

Validation is intentionally separate from dataset generation.  A dataset is
never labelled validated merely because it was written to disk.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable

from ..config import (
    DEFAULT_PARAMETERS,
    PAPER_DOI,
    PAPER_REFERENCE_HW_M,
    PAPER_REFERENCE_TOLERANCE_M,
    PAPER_REFERENCE_TOE_M,
    WALL_LOCATIONS_M,
)
from ..models.analytical_model import (
    _head_at,
    compute_core,
    head_dimensionless,
    run_no_wall_baseline,
    run_simulation,
)
from ..models.parameters import Parameters, compute_derived
from ..models.scenarios import classify_scenario

MATH_TOL = 1e-6
FLUX_TOL = 1e-7


def _check(
    check_id: str,
    layer: str,
    name: str,
    status: str,
    source: str,
    *,
    reference: float | str | None = None,
    computed: float | str | None = None,
    tolerance: float | None = None,
    units: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    abs_diff = None
    rel_diff = None
    if isinstance(reference, (int, float)) and isinstance(computed, (int, float)):
        abs_diff = abs(float(computed) - float(reference))
        rel_diff = abs_diff / abs(float(reference)) if float(reference) != 0 else None
    return {
        "check_id": check_id,
        "layer": layer,
        "name": name,
        "status": status,
        "reference": reference,
        "computed": computed,
        "absolute_difference": abs_diff,
        "relative_difference": rel_diff,
        "tolerance": tolerance,
        "units": units,
        "source": source,
        "notes": notes,
    }


def _numeric_check(
    check_id: str,
    layer: str,
    name: str,
    reference: float,
    computed: float,
    tolerance: float,
    source: str,
    *,
    units: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    ok = math.isfinite(computed) and abs(computed - reference) <= tolerance
    return _check(
        check_id,
        layer,
        name,
        "passed" if ok else "failed",
        source,
        reference=reference,
        computed=computed,
        tolerance=tolerance,
        units=units,
        notes=notes,
    )


def _paper_parameters_match(parameters: Parameters) -> bool:
    for field, expected in DEFAULT_PARAMETERS.items():
        actual = getattr(parameters, field)
        if not math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-12):
            return False
    return True


def _paper_case(correction_mode: str, L_w: float, h_w: float) -> Parameters:
    return Parameters(
        **DEFAULT_PARAMETERS,
        L_w_m=L_w,
        h_w_m=h_w,
        correction_mode=correction_mode,  # type: ignore[arg-type]
    )


def _scenario_geometric_ok(core, parameters: Parameters) -> bool:
    scenario = core.classification.scenario_id
    wall_right = parameters.L_w_m + parameters.wall_thickness_m
    if scenario == "a":
        return core.toe_m <= parameters.L_w_m + 1e-7
    if scenario == "b":
        return parameters.L_w_m < core.toe_m < wall_right
    if scenario == "c":
        return core.toe_m >= wall_right - 1e-7
    if scenario == "d":
        return core.xh_m <= wall_right + 1e-7 and core.toe_m <= wall_right + 1e-7
    if scenario == "e":
        return core.xh_m <= wall_right + 1e-7 and core.toe_m >= wall_right - 1e-7
    if scenario == "f":
        return core.xh_m >= wall_right - 1e-7
    return False


def _head_continuity_error(parameters: Parameters) -> tuple[float, str]:
    derived = compute_derived(parameters)
    core = compute_core(parameters, derived)
    scenario = core.classification.scenario_id
    Lb = parameters.L_w_m / derived.x_t_no_wall_m
    wb = parameters.wall_thickness_m / derived.x_t_no_wall_m
    hb = parameters.h_w_m / parameters.H_m
    xh_bar = core.xh_bar
    boundaries: list[tuple[str, float]] = []
    if scenario in ("b", "c", "d", "e", "f"):
        boundaries.append(("L_w", Lb))
    if scenario in ("c", "e", "f"):
        boundaries.append(("L_w + w", Lb + wb))
    if scenario in ("d", "e"):
        boundaries.append(("x_h", xh_bar))
    if not boundaries:
        return 0.0, "no sub-zone boundaries"

    # x_h can sit extremely close to L_w because kappa is of order 1e-4.
    # A small offset avoids mistaking the steep but continuous square-root
    # derivative for a head discontinuity.
    eps = 1e-11
    max_jump = 0.0
    worst = ""
    for label, xb in boundaries:
        left = max(0.0, xb - eps)
        right = xb + eps
        if xb <= 1e-9:
            continue
        try:
            h_left = head_dimensionless(left, scenario, parameters, derived, xh_bar)
            h_right = head_dimensionless(right, scenario, parameters, derived, xh_bar)
        except Exception as exc:
            return float("inf"), f"{label}: {exc}"
        jump = abs(h_right - h_left) * parameters.H_m
        if jump > max_jump:
            max_jump = jump
            worst = label
    return max_jump, worst


def _toe_head_error(parameters: Parameters) -> float:
    derived = compute_derived(parameters)
    core = compute_core(parameters, derived)
    phi_bar = head_dimensionless(
        core.toe_bar,
        core.classification.scenario_id,
        parameters,
        derived,
        core.xh_bar,
    )
    phi = derived.phi_s_m + parameters.H_m * phi_bar
    return abs(phi - derived.phi_t_m)


def run_validation(
    correction_mode: str = "pool_carrera_flux",
    parameters: Parameters | None = None,
    *,
    paper_checks: bool = True,
) -> dict[str, Any]:
    """Run implementation invariants and paper-reference comparisons."""

    checked_at = datetime.now(timezone.utc).isoformat()
    if parameters is None:
        base_parameters = _paper_case(correction_mode, 0.0, PAPER_REFERENCE_HW_M)
    else:
        base_parameters = parameters.model_copy(
            update={"correction_mode": correction_mode}
        )

    derived = compute_derived(base_parameters)
    checks: list[dict[str, Any]] = []

    checks.append(
        _numeric_check(
            "alpha_base",
            "mathematical",
            "Density ratio alpha = rho_f / (rho_s - rho_f)",
            base_parameters.alpha_base,
            derived.alpha_base,
            1e-12,
            "Sun et al. (2026), Eq. (2)",
            units="-",
            notes="Algorithm 1 contains an inverted alpha expression; Eq. (2) is used.",
        )
    )
    checks.append(
        _numeric_check(
            "kappa",
            "mathematical",
            "Conductivity ratio kappa = K_w / K_a",
            base_parameters.kappa,
            derived.kappa,
            1e-15,
            "Sun et al. (2026), Eq. (8)",
            units="-",
        )
    )
    expected_alpha = (
        base_parameters.alpha_base
        / (
            1.0
            - (base_parameters.alpha_T_m / base_parameters.H_m) ** (1.0 / 6.0)
        )
        if correction_mode == "pool_carrera_flux"
        else base_parameters.alpha_base
    )
    checks.append(
        _numeric_check(
            "alpha_effective",
            "mathematical",
            "Effective density ratio used by the selected correction mode",
            expected_alpha,
            derived.alpha_effective,
            1e-9,
            "Sun et al. (2026), Eq. (43)",
            units="-",
            notes="Eq. (43) correction is applied by replacing alpha with alpha prime.",
        )
    )

    # Conditions over the 16 paper configurations.
    case_parameters = [
        _paper_case(correction_mode, L_w, h_w)
        for L_w in WALL_LOCATIONS_M
        for h_w in (6.0, 12.0, 18.0, 24.0)
    ]
    toe_errors = [_toe_head_error(p) for p in case_parameters]
    continuity_errors = [_head_continuity_error(p)[0] for p in case_parameters]
    flux_errors: list[float] = []
    scenario_ok = 0
    for p in case_parameters:
        d = compute_derived(p)
        core = compute_core(p, d)
        phi_toe = _head_at(core.toe_m, p, d, core)
        phi_L = _head_at(p.domain_length_m, p, d, core)
        slope = (phi_L - phi_toe) / (p.domain_length_m - core.toe_m)
        flux = p.K_a_m_per_day * p.H_m * slope
        flux_errors.append(abs(flux - p.q_f_m2_per_day) / p.q_f_m2_per_day)
        if _scenario_geometric_ok(core, p):
            scenario_ok += 1

    checks.append(
        _numeric_check(
            "toe_head_condition",
            "mathematical",
            "phi(x_t) = (1 + 1/alpha) H_s for all 16 paper configurations",
            0.0,
            max(toe_errors),
            MATH_TOL,
            "Sun et al. (2026), Eq. (6)",
            units="m",
            notes="Maximum absolute error over the 16 configurations.",
        )
    )
    checks.append(
        _numeric_check(
            "head_continuity",
            "mathematical",
            "Hydraulic-head continuity at sub-zone boundaries",
            0.0,
            max(continuity_errors),
            MATH_TOL,
            "Sun et al. (2026), Eq. (5) and Eqs. (A9), (A17), (A22), (A27), (A33)",
            units="m",
            notes="Maximum jump at L_w, L_w + w and x_h over the 16 configurations.",
        )
    )
    checks.append(
        _numeric_check(
            "inland_flux_bc",
            "mathematical",
            "Constant inland flux boundary condition",
            0.0,
            max(flux_errors),
            FLUX_TOL,
            "Sun et al. (2026), Eq. (4)",
            units="-",
            notes="Maximum relative error of K_a H dphi/dx / q_f over the 16 configurations.",
        )
    )
    checks.append(
        _numeric_check(
            "scenario_geometry",
            "mathematical",
            "Scenario geometry is self-consistent",
            float(len(case_parameters)),
            float(scenario_ok),
            0.0,
            "Sun et al. (2026), Table 1 and Eq. (23)",
            units="cases",
            notes="Toe/x_h positions checked against the assigned scenario over all 16 configurations.",
        )
    )

    # Coast and interface endpoint checks for a representative case.
    representative = _paper_case(correction_mode, 0.0, PAPER_REFERENCE_HW_M)
    d_rep = compute_derived(representative)
    core_rep = compute_core(representative, d_rep)
    phi0 = _head_at(0.0, representative, d_rep, core_rep)
    zeta0 = (d_rep.alpha_effective + 1.0) * representative.H_s_m - d_rep.alpha_effective * phi0
    phi_toe_rep = _head_at(core_rep.toe_m, representative, d_rep, core_rep)
    zeta_toe = (
        (d_rep.alpha_effective + 1.0) * representative.H_s_m
        - d_rep.alpha_effective * phi_toe_rep
    )
    checks.append(
        _numeric_check(
            "coast_bc",
            "mathematical",
            "Coast boundary condition phi(0) = (1 + 1/alpha) H_s - H/alpha",
            d_rep.phi_s_m,
            phi0,
            MATH_TOL,
            "Sun et al. (2026), Eq. (3)",
            units="m",
        )
    )
    checks.append(
        _numeric_check(
            "interface_endpoints",
            "mathematical",
            "Interface elevation zeta(0) = H and zeta(x_t) = 0",
            0.0,
            max(abs(zeta0 - representative.H_m), abs(zeta_toe)),
            MATH_TOL,
            "Sun et al. (2026), Eq. (7)",
            units="m",
        )
    )

    # Paper comparisons.
    paper_applicable = bool(paper_checks and _paper_parameters_match(base_parameters) and correction_mode == "pool_carrera_flux")
    if not paper_applicable:
        reason = (
            "Paper-reference toe checks require the Table 2 parameters and the "
            "Pool-Carrera correction (Eq. 43)."
        )
        for check_id, name, ref in [
            ("paper_no_wall", "No-wall interface toe (paper reference)", PAPER_REFERENCE_TOE_M["no_wall"]),
            ("paper_Lw0", "Toe for L_w = 0 m, h_w = 12 m", PAPER_REFERENCE_TOE_M["Lw=0,hw=12"]),
            ("paper_Lw38", "Toe for L_w = 38 m, h_w = 12 m", PAPER_REFERENCE_TOE_M["Lw=38,hw=12"]),
            ("paper_Lw77", "Toe for L_w = 77 m, h_w = 12 m", PAPER_REFERENCE_TOE_M["Lw=77,hw=12"]),
            ("paper_Lw115", "Toe for L_w = 115 m, h_w = 12 m", PAPER_REFERENCE_TOE_M["Lw=115,hw=12"]),
        ]:
            checks.append(
                _check(
                    check_id,
                    "paper",
                    name,
                    "not_applicable",
                    "Sun et al. (2026), Section 3.1, p. 8",
                    reference=ref,
                    tolerance=PAPER_REFERENCE_TOLERANCE_M,
                    units="m",
                    notes=reason,
                )
            )
        paper_status = "not_applicable"
    else:
        no_wall = run_no_wall_baseline(
            parameters=_paper_case("pool_carrera_flux", 0.0, PAPER_REFERENCE_HW_M)
        )
        checks.append(
            _numeric_check(
                "paper_no_wall",
                "paper",
                "No-wall interface toe (paper reference)",
                PAPER_REFERENCE_TOE_M["no_wall"],
                no_wall.toe_location_x_t_m,
                PAPER_REFERENCE_TOLERANCE_M,
                "Sun et al. (2026), Section 3.1, p. 8 (reported x_t^a = 191.7 m)",
                units="m",
                notes="Corrected analytical model (Eq. 43).",
            )
        )
        for L_w, key in [
            (0.0, "Lw=0,hw=12"),
            (38.0, "Lw=38,hw=12"),
            (77.0, "Lw=77,hw=12"),
            (115.0, "Lw=115,hw=12"),
        ]:
            result = run_simulation(
                _paper_case("pool_carrera_flux", L_w, PAPER_REFERENCE_HW_M),
                include_profiles=False,
            )
            checks.append(
                _numeric_check(
                    f"paper_Lw{int(L_w)}",
                    "paper",
                    f"Toe for L_w = {int(L_w)} m, h_w = 12 m",
                    PAPER_REFERENCE_TOE_M[key],
                    result.toe_location_x_t_m,
                    PAPER_REFERENCE_TOLERANCE_M,
                    "Sun et al. (2026), Section 3.1, p. 8; panels *2",
                    units="m",
                    notes=(
                        "The paper text calls panels *2 an 18 m cutoff-wall case, "
                        "but the Fig. 4 caption defines index 2 as h_w = 12 m. "
                        "The 12 m equation input reproduces the reported values."
                    ),
                )
            )
        paper_status = "passed" if all(c["status"] == "passed" for c in checks if c["layer"] == "paper") else "failed"

    math_status = "passed" if all(c["status"] == "passed" for c in checks if c["layer"] == "mathematical") else "failed"
    if math_status == "passed" and paper_status == "passed":
        validation_status = "passed"
    elif paper_status == "not_applicable" and math_status == "passed":
        validation_status = "not_applicable"
    else:
        validation_status = "failed"

    passed = sum(1 for c in checks if c["status"] == "passed")
    failed = sum(1 for c in checks if c["status"] == "failed")
    na = sum(1 for c in checks if c["status"] == "not_applicable")

    return {
        "validation_status": validation_status,
        "math_status": math_status,
        "paper_status": paper_status,
        "total_checks": len(checks),
        "passed_checks": passed,
        "failed_checks": failed,
        "not_applicable_checks": na,
        "checks": checks,
        "metadata": {
            "checked_at": checked_at,
            "paper_doi": PAPER_DOI,
            "correction_mode": correction_mode,
            "paper_reference_hw_m": PAPER_REFERENCE_HW_M,
            "paper_tolerance_m": PAPER_REFERENCE_TOLERANCE_M,
            "note": (
                "Validation compares the corrected analytical toe locations with text-reported "
                "values. No SEAWAT simulation or field data validation was performed in this project."
            ),
        },
    }
