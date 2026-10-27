"""Confined-aquifer analytical model with a cutoff wall.

Implements the constant-inland-flux branch of Sun et al. (2026), Advances in
Water Resources 212, 105301.  Equation numbers in comments refer to that
paper.

The implementation follows the dimensionless formulation in Eqs. (8)-(23)
and recovers dimensional quantities with the same definitions.  The optional
Pool-Carrera correction (Eq. 43) is applied by replacing alpha with alpha'.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite, sqrt
from typing import Any

from .parameters import DerivedParameters, Parameters, compute_derived
from .scenarios import (
    ClassificationResult,
    ScenarioClassificationError,
    classify_scenario,
)


class ModelError(RuntimeError):
    """Raised when the analytical equations cannot be evaluated."""


def _sqrt(value: float, context: str) -> float:
    if value < -1e-10:
        raise ModelError(f"negative square-root argument in {context}: {value:.8g}")
    return sqrt(max(0.0, value))


def _check_finite(value: float, context: str) -> float:
    if not isfinite(value):
        raise ModelError(f"non-finite result in {context}: {value!r}")
    return value


def xh_dimensionless(L_w_bar: float, h_w_bar: float, kappa: float) -> float:
    """Dimensionless x_h from Eq. (A25)."""

    return L_w_bar * (1.0 - kappa) + kappa * (1.0 - h_w_bar) ** 2


def toe_dimensionless(
    scenario_id: str,
    L_w_bar: float,
    h_w_bar: float,
    w_bar: float,
    kappa: float,
) -> float:
    """Dimensionless toe location from Eqs. (17)-(22)."""

    beta1 = (1.0 - h_w_bar) * (1.0 - kappa)
    lam1 = beta1 - _sqrt(L_w_bar, "Eq. (13) lambda_1")

    if scenario_id == "a":
        value = 1.0
    elif scenario_id == "b":
        value = 1.0 - 2.0 * beta1 * (1.0 - _sqrt(L_w_bar, "Eq. (18) sqrt(L_w_bar)"))
    elif scenario_id == "c":
        value = 1.0 - 2.0 * beta1 * (
            lam1 + _sqrt(lam1 * lam1 + w_bar, "Eq. (19) sqrt(lambda_1^2 + w)")
        )
    elif scenario_id == "d":
        value = (h_w_bar**2 + L_w_bar) * (1.0 - kappa) + kappa
    elif scenario_id == "e":
        inside = kappa * L_w_bar + w_bar - beta1 * beta1 * kappa / (1.0 - kappa)
        value = (3.0 - 2.0 * kappa) * kappa - (
            2.0 * beta1 * _sqrt(inside, "Eq. (21) sqrt(kappa L_w + w - ...)")
            - h_w_bar * (2.0 - h_w_bar) * (1.0 - kappa) * (1.0 - 2.0 * kappa)
            - (1.0 - kappa) * L_w_bar
        )
    elif scenario_id == "f":
        value = 1.0 + w_bar * (1.0 - 1.0 / kappa)
    else:
        raise ModelError(f"unsupported scenario id: {scenario_id!r}")

    return _check_finite(value, f"toe location for scenario {scenario_id}")


def head_dimensionless(
    x_bar: float,
    scenario_id: str,
    parameters: Parameters,
    derived: DerivedParameters,
    xh_bar: float,
) -> float:
    """Dimensionless hydraulic head from Eqs. (9)-(16).

    ``x_bar = x / x_t^a`` and the returned value is
    ``(phi - phi_s) / H``.  The caller is responsible for only asking for
    x <= x_t.
    """

    if x_bar < -1e-12:
        raise ModelError(f"x_bar must be non-negative, got {x_bar}")

    kappa = derived.kappa
    alpha = derived.alpha_effective
    Lb = parameters.L_w_m / derived.x_t_no_wall_m
    hb = parameters.h_w_m / parameters.H_m
    wb = parameters.wall_thickness_m / derived.x_t_no_wall_m
    beta1 = (1.0 - hb) * (1.0 - kappa)
    lam1 = beta1 - _sqrt(Lb, "Eq. (13) lambda_1")

    def phi_a(value: float) -> float:
        return _sqrt(value, "Eq. (9) phi_a") / alpha

    def phi_b2(value: float) -> float:
        inside = value + beta1 * (beta1 - 2.0 * _sqrt(Lb, "Eq. (10) sqrt(L_w_bar)"))
        return (_sqrt(inside, "Eq. (10) phi_b") + beta1) / alpha

    def phi_c3(value: float) -> float:
        inside = value + 2.0 * beta1 * lam1 + 2.0 * beta1 * _sqrt(
            lam1 * lam1 + wb, "Eq. (12) sqrt(lambda_1^2 + w)"
        )
        return _sqrt(inside, "Eq. (12) phi_c") / alpha

    def phi_d2(value: float) -> float:
        inside = (value - (1.0 - kappa) * Lb) / kappa
        return _sqrt(inside, "Eq. (14) phi_d zone 2") / alpha

    def phi_d3(value: float) -> float:
        inside = value - kappa * beta1 * beta1 / (1.0 - kappa) - (1.0 - kappa) * Lb
        return (_sqrt(inside, "Eq. (14) phi_d zone 3") + beta1) / alpha

    def phi_e4(value: float) -> float:
        inside_sqrt = kappa * Lb + wb - kappa * beta1 * beta1 / (1.0 - kappa)
        correction = (
            (1.0 - 2.0 * kappa) / (1.0 - kappa) * beta1
            + 2.0 * _sqrt(inside_sqrt, "Eq. (15) inner square root")
        )
        inside = value - (1.0 - kappa) * Lb + beta1 * correction
        return _sqrt(inside, "Eq. (15) phi_e") / alpha

    def phi_f3(value: float) -> float:
        inside = value - (1.0 - 1.0 / kappa) * wb
        return _sqrt(inside, "Eq. (16) phi_f") / alpha

    eps = 1e-12
    if scenario_id == "a":
        return phi_a(x_bar)
    if scenario_id == "b":
        return phi_a(x_bar) if x_bar <= Lb + eps else phi_b2(x_bar)
    if scenario_id == "c":
        if x_bar <= Lb + eps:
            return phi_a(x_bar)
        if x_bar <= Lb + wb + eps:
            return phi_b2(x_bar)
        return phi_c3(x_bar)
    if scenario_id == "d":
        if x_bar <= Lb + eps:
            return phi_a(x_bar)
        if x_bar <= xh_bar + eps:
            return phi_d2(x_bar)
        return phi_d3(x_bar)
    if scenario_id == "e":
        if x_bar <= Lb + eps:
            return phi_a(x_bar)
        if x_bar <= xh_bar + eps:
            return phi_d2(x_bar)
        if x_bar <= Lb + wb + eps:
            return phi_d3(x_bar)
        return phi_e4(x_bar)
    if scenario_id == "f":
        if x_bar <= Lb + eps:
            return phi_a(x_bar)
        if x_bar <= Lb + wb + eps:
            return phi_d2(x_bar)
        return phi_f3(x_bar)
    raise ModelError(f"unsupported scenario id: {scenario_id!r}")


@dataclass
class CoreResult:
    classification: ClassificationResult
    toe_bar: float
    toe_m: float
    xh_bar: float
    xh_m: float
    warnings: list[str] = field(default_factory=list)


def compute_core(parameters: Parameters, derived: DerivedParameters) -> CoreResult:
    """Classify a case and compute its toe and wall-intersection location."""

    classification = classify_scenario(parameters, derived)
    Lb = parameters.L_w_m / derived.x_t_no_wall_m
    hb = parameters.h_w_m / parameters.H_m
    wb = parameters.wall_thickness_m / derived.x_t_no_wall_m

    toe_bar = toe_dimensionless(
        classification.scenario_id, Lb, hb, wb, derived.kappa
    )
    toe_m = toe_bar * derived.x_t_no_wall_m
    xh_bar = xh_dimensionless(Lb, hb, derived.kappa)
    xh_m = xh_bar * derived.x_t_no_wall_m

    warnings = list(classification.warnings)
    if parameters.L_w_m == 0.0:
        warnings.append(
            "L_w = 0 is a cutoff wall at the coastline, not a no-wall baseline."
        )
    if toe_m <= 0.0:
        warnings.append("Computed interface toe is non-positive; check the configuration.")
    if toe_m > parameters.domain_length_m:
        warnings.append(
            "Interface toe lies beyond the configured profile domain L; "
            "the profile will be extended to include it."
        )

    wall_right = parameters.L_w_m + parameters.wall_thickness_m
    scenario = classification.scenario_id
    if scenario == "a" and not (toe_m <= parameters.L_w_m + 1e-7):
        warnings.append("Scenario (a) consistency: toe is not seaward of L_w.")
    if scenario == "b" and not (parameters.L_w_m < toe_m < wall_right):
        warnings.append("Scenario (b) consistency: toe is not between L_w and L_w + w.")
    if scenario == "c" and not (toe_m > wall_right - 1e-7):
        warnings.append("Scenario (c) consistency: toe is not inland of L_w + w.")
    if scenario in ("d", "e") and xh_m > wall_right + 1e-7:
        warnings.append("Scenario (d/e) consistency: x_h lies beyond L_w + w.")
    if scenario == "d" and not (toe_m <= wall_right + 1e-7):
        warnings.append("Scenario (d) consistency: toe is not beneath the wall thickness.")
    if scenario == "e" and not (toe_m >= wall_right - 1e-7):
        warnings.append("Scenario (e) consistency: toe is not inland of L_w + w.")
    if scenario == "f" and xh_m < wall_right - 1e-7:
        warnings.append("Scenario (f) consistency: x_h is not beyond L_w + w.")

    return CoreResult(
        classification=classification,
        toe_bar=toe_bar,
        toe_m=toe_m,
        xh_bar=xh_bar,
        xh_m=xh_m,
        warnings=warnings,
    )


@dataclass
class SimulationResult:
    case_id: str
    status: str
    scenario_id: str
    scenario_title: str
    scenario_description: str
    scenario_condition: str
    toe_location_x_t_m: float
    toe_dimensionless: float
    toe_location_uncorrected_m: float
    uncorrected_scenario_id: str
    xh_m: float
    x_t_no_wall_m: float
    head_at_inland_boundary_m: float | None
    profiles: list[dict[str, Any]]
    warnings: list[str]
    parameters: dict[str, Any]
    derived: dict[str, Any]
    classification: dict[str, Any]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "scenario_id": self.scenario_id,
            "scenario_title": self.scenario_title,
            "scenario_description": self.scenario_description,
            "scenario_condition": self.scenario_condition,
            "toe_location_x_t_m": self.toe_location_x_t_m,
            "toe_dimensionless": self.toe_dimensionless,
            "toe_location_uncorrected_m": self.toe_location_uncorrected_m,
            "uncorrected_scenario_id": self.uncorrected_scenario_id,
            "xh_m": self.xh_m,
            "x_t_no_wall_m": self.x_t_no_wall_m,
            "head_at_inland_boundary_m": self.head_at_inland_boundary_m,
            "profiles": self.profiles,
            "warnings": self.warnings,
            "parameters": self.parameters,
            "derived": self.derived,
            "classification": self.classification,
            "metadata": self.metadata,
        }


def _head_at(
    x_m: float,
    parameters: Parameters,
    derived: DerivedParameters,
    core: CoreResult,
) -> float:
    x_bar = x_m / derived.x_t_no_wall_m
    toe_m = core.toe_m
    if x_m <= toe_m + 1e-9:
        phi_bar = head_dimensionless(
            x_bar,
            core.classification.scenario_id,
            parameters,
            derived,
            core.xh_bar,
        )
        return _check_finite(
            derived.phi_s_m + parameters.H_m * phi_bar,
            f"hydraulic head at x={x_m:.6g} m",
        )
    # Beyond the toe the flow path has thickness h = H.  From Eq. (A1) with
    # h = H, q_f = K_a H dphi/dx, so the head is linear in the freshwater zone.
    slope = parameters.q_f_m2_per_day / (
        parameters.K_a_m_per_day * parameters.H_m
    )
    return _check_finite(
        derived.phi_t_m + slope * (x_m - toe_m),
        f"freshwater-zone head at x={x_m:.6g} m",
    )


def run_simulation(
    parameters: Parameters,
    *,
    case_id: str = "single",
    include_profiles: bool = True,
    profile_points: int = 401,
) -> SimulationResult:
    """Run one complete analytical simulation.

    The selected correction mode determines the primary toe and profile.  The
    uncorrected sharp-interface toe (alpha = 40) is always computed for
    transparency, but its profile is not returned.
    """

    from .profiles import build_profiles  # local import avoids a cycle

    derived = compute_derived(parameters)
    core = compute_core(parameters, derived)
    warnings = list(core.warnings)

    # Uncorrected comparison result.
    derived_none = compute_derived(parameters, force_no_correction=True)
    core_none = compute_core(parameters, derived_none)

    if include_profiles:
        profiles = build_profiles(
            parameters,
            derived,
            core,
            profile_points=profile_points,
            warnings=warnings,
        )
    else:
        profiles = []

    phi_L = _head_at(parameters.domain_length_m, parameters, derived, core)

    metadata = {
        "model_version": "sun2026-confined-cutoff-v1",
        "paper_doi": "10.1016/j.advwatres.2026.105301",
        "paper_equations": {
            "governing": ["Eqs. (1)-(7)"],
            "dimensionless": ["Eq. (8)"],
            "head": ["Eqs. (9)-(16)", "Appendix A Eqs. (A3)-(A38)"],
            "toe": ["Eqs. (17)-(22)", "Appendix A Eqs. (A6)-(A39)"],
            "scenario_classification": ["Eq. (23)"],
            "mixing_correction": ["Eq. (43)"],
        },
        "correction_mode": parameters.correction_mode,
        "note": (
            "Head for x > x_t is extended linearly from q_f = K_a H dphi/dx; "
            "the interface elevation is undefined inland of the toe."
        ),
    }

    return SimulationResult(
        case_id=case_id,
        status="success",
        scenario_id=core.classification.scenario_id,
        scenario_title=core.classification.definition.title,
        scenario_description=core.classification.definition.description,
        scenario_condition=core.classification.definition.condition_text,
        toe_location_x_t_m=core.toe_m,
        toe_dimensionless=core.toe_bar,
        toe_location_uncorrected_m=core_none.toe_m,
        uncorrected_scenario_id=core_none.classification.scenario_id,
        xh_m=core.xh_m,
        x_t_no_wall_m=derived.x_t_no_wall_m,
        head_at_inland_boundary_m=phi_L,
        profiles=profiles,
        warnings=warnings,
        parameters=parameters.model_dump(),
        derived=derived.as_dict(),
        classification={
            "scenario_id": core.classification.scenario_id,
            "all_matches": core.classification.all_matches,
            "dimensionless": core.classification.dimensionless,
        },
        metadata=metadata,
    )


def run_no_wall_baseline(
    *,
    case_id: str = "no_wall",
    include_profiles: bool = False,
    parameters: Parameters | None = None,
) -> SimulationResult:
    """Explicit no-cutoff-wall baseline using scenario (a).

    This is not the same configuration as ``L_w = 0``.  The paper's no-wall
    toe is x_t^a = H^2 / gamma1.
    """

    if parameters is None:
        from ..config import DEFAULT_PARAMETERS

        parameters = Parameters(
            **DEFAULT_PARAMETERS,
            L_w_m=0.0,
            h_w_m=1e-9,
            correction_mode="pool_carrera_flux",
        )
    # The interface solution for scenario (a) is independent of L_w and h_w.
    # Use a wall outside the domain so the geometry is unambiguous.
    baseline = parameters.model_copy(
        update={
            "L_w_m": parameters.domain_length_m - parameters.wall_thickness_m,
            "h_w_m": parameters.H_m * 0.999,
        }
    )
    derived = compute_derived(baseline)
    classification = classify_scenario(baseline, derived)
    toe_bar = toe_dimensionless(
        classification.scenario_id,
        baseline.L_w_m / derived.x_t_no_wall_m,
        baseline.h_w_m / baseline.H_m,
        baseline.wall_thickness_m / derived.x_t_no_wall_m,
        derived.kappa,
    )
    from .scenarios import ScenarioDefinition

    baseline_definition = ScenarioDefinition(
        scenario_id=classification.scenario_id,
        title="No cutoff wall (baseline)",
        description="Analytical interface toe in the absence of a cutoff wall.",
        condition_text="x_t = x_t^a = H^2 / gamma1",
    )
    baseline_classification = ClassificationResult(
        scenario_id=classification.scenario_id,
        definition=baseline_definition,
        dimensionless=classification.dimensionless,
        all_matches=classification.all_matches,
        warnings=["Explicit no-wall baseline; L_w is not set to zero."],
    )
    core = CoreResult(
        classification=baseline_classification,
        toe_bar=toe_bar,
        toe_m=toe_bar * derived.x_t_no_wall_m,
        xh_bar=xh_dimensionless(
            baseline.L_w_m / derived.x_t_no_wall_m,
            baseline.h_w_m / baseline.H_m,
            derived.kappa,
        ),
        xh_m=0.0,
        warnings=["Explicit no-wall baseline; L_w is not set to zero."],
    )
    if include_profiles:
        from .profiles import build_profiles

        profiles = build_profiles(
            baseline,
            derived,
            core,
            profile_points=401,
            warnings=core.warnings,
        )
    else:
        profiles = []
    phi_L = _head_at(baseline.domain_length_m, baseline, derived, core)
    return SimulationResult(
        case_id=case_id,
        status="success",
        scenario_id=core.classification.scenario_id,
        scenario_title=core.classification.definition.title,
        scenario_description=core.classification.definition.description,
        scenario_condition=core.classification.definition.condition_text,
        toe_location_x_t_m=core.toe_m,
        toe_dimensionless=core.toe_bar,
        toe_location_uncorrected_m=compute_core(
            baseline, compute_derived(baseline, force_no_correction=True)
        ).toe_m,
        uncorrected_scenario_id="a",
        xh_m=core.xh_m,
        x_t_no_wall_m=derived.x_t_no_wall_m,
        head_at_inland_boundary_m=phi_L,
        profiles=profiles,
        warnings=core.warnings,
        parameters=baseline.model_dump(),
        derived=derived.as_dict(),
        classification={
            "scenario_id": classification.scenario_id,
            "all_matches": classification.all_matches,
            "dimensionless": classification.dimensionless,
        },
        metadata={
            "model_version": "sun2026-confined-cutoff-v1",
            "paper_doi": "10.1016/j.advwatres.2026.105301",
            "correction_mode": baseline.correction_mode,
            "baseline": True,
        },
    )


__all__ = [
    "CoreResult",
    "ModelError",
    "ScenarioClassificationError",
    "SimulationResult",
    "compute_core",
    "head_dimensionless",
    "run_no_wall_baseline",
    "run_simulation",
    "toe_dimensionless",
    "xh_dimensionless",
]
