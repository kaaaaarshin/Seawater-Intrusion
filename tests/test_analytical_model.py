from __future__ import annotations

import math

import pytest

from app.config import (
    DEFAULT_PARAMETERS,
    PAPER_REFERENCE_HW_M,
    PAPER_REFERENCE_TOE_M,
    PAPER_REFERENCE_TOLERANCE_M,
)
from app.models.analytical_model import (
    _head_at,
    compute_core,
    head_dimensionless,
    run_no_wall_baseline,
    run_simulation,
    toe_dimensionless,
    xh_dimensionless,
)
from app.models.parameters import Parameters, compute_derived


def paper_parameters(**overrides) -> Parameters:
    values = {**DEFAULT_PARAMETERS, "L_w_m": 0.0, "h_w_m": 12.0}
    values.update(overrides)
    return Parameters(**values)


@pytest.mark.parametrize(
    ("L_w", "key"),
    [
        (0.0, "Lw=0,hw=12"),
        (38.0, "Lw=38,hw=12"),
        (77.0, "Lw=77,hw=12"),
        (115.0, "Lw=115,hw=12"),
    ],
)
def test_corrected_toe_matches_paper_text(L_w: float, key: str) -> None:
    result = run_simulation(
        paper_parameters(L_w_m=L_w, h_w_m=PAPER_REFERENCE_HW_M),
        include_profiles=False,
    )
    reference = PAPER_REFERENCE_TOE_M[key]
    assert result.toe_location_x_t_m == pytest.approx(
        reference, abs=PAPER_REFERENCE_TOLERANCE_M
    )


def test_no_wall_baseline_matches_paper() -> None:
    result = run_no_wall_baseline()
    assert result.scenario_id == "a"
    assert result.toe_location_x_t_m == pytest.approx(
        PAPER_REFERENCE_TOE_M["no_wall"], abs=PAPER_REFERENCE_TOLERANCE_M
    )
    assert result.toe_location_x_t_m == pytest.approx(191.71959564551693)


def test_zero_wall_distance_is_not_the_no_wall_baseline() -> None:
    walled = run_simulation(paper_parameters(L_w_m=0.0, h_w_m=12.0), include_profiles=False)
    baseline = run_no_wall_baseline()
    assert walled.scenario_id == "e"
    assert walled.toe_location_x_t_m < baseline.toe_location_x_t_m
    assert baseline.toe_location_x_t_m - walled.toe_location_x_t_m > 80.0
    assert any("not a no-wall baseline" in warning for warning in walled.warnings)


def test_coast_and_toe_conditions() -> None:
    parameters = paper_parameters(L_w_m=38.0, h_w_m=12.0)
    derived = compute_derived(parameters)
    core = compute_core(parameters, derived)

    assert _head_at(0.0, parameters, derived, core) == pytest.approx(
        derived.phi_s_m
    )
    assert _head_at(core.toe_m, parameters, derived, core) == pytest.approx(
        derived.phi_t_m, abs=1e-9
    )

    zeta_coast = (derived.alpha_effective + 1.0) * parameters.H_s_m - (
        derived.alpha_effective * _head_at(0.0, parameters, derived, core)
    )
    assert zeta_coast == pytest.approx(parameters.H_m)


def test_constant_inland_flux_is_recovered() -> None:
    parameters = paper_parameters(L_w_m=77.0, h_w_m=12.0)
    derived = compute_derived(parameters)
    core = compute_core(parameters, derived)
    phi_toe = _head_at(core.toe_m, parameters, derived, core)
    phi_L = _head_at(parameters.domain_length_m, parameters, derived, core)
    flux = (
        parameters.K_a_m_per_day
        * parameters.H_m
        * (phi_L - phi_toe)
        / (parameters.domain_length_m - core.toe_m)
    )
    assert flux == pytest.approx(parameters.q_f_m2_per_day, rel=1e-9)


def test_profiles_are_finite_and_interface_ends_at_toe() -> None:
    parameters = paper_parameters(L_w_m=0.0, h_w_m=12.0)
    result = run_simulation(parameters, profile_points=101)
    assert len(result.profiles) > 101
    assert result.profiles[0]["x_m"] == 0.0
    assert result.profiles[-1]["x_m"] == pytest.approx(parameters.domain_length_m)
    assert result.profiles[0]["interface_elevation_zeta_m"] == pytest.approx(
        parameters.H_m
    )
    assert all(
        math.isfinite(point["hydraulic_head_phi_m"])
        for point in result.profiles
    )
    toe_points = [
        point
        for point in result.profiles
        if abs(point["x_m"] - result.toe_location_x_t_m) < 1e-6
    ]
    assert len(toe_points) == 1
    assert toe_points[0]["interface_elevation_zeta_m"] == pytest.approx(0.0, abs=1e-8)
    assert any(
        point["x_m"] > result.toe_location_x_t_m
        and point["interface_elevation_zeta_m"] is None
        for point in result.profiles
    )


def test_profiles_extend_beyond_short_domain() -> None:
    parameters = paper_parameters(
        L_w_m=115.0,
        h_w_m=12.0,
        domain_length_m=150.0,
    )
    result = run_simulation(parameters, profile_points=51)
    assert result.toe_location_x_t_m > parameters.domain_length_m
    assert result.profiles[-1]["x_m"] > result.toe_location_x_t_m
    assert any("extended" in warning for warning in result.warnings)


def test_uncorrected_toe_is_reported_separately() -> None:
    corrected = run_simulation(
        paper_parameters(L_w_m=38.0, h_w_m=12.0), include_profiles=False
    )
    uncorrected = run_simulation(
        paper_parameters(L_w_m=38.0, h_w_m=12.0, correction_mode="none"),
        include_profiles=False,
    )
    assert corrected.toe_location_uncorrected_m == pytest.approx(
        216.89801264894433
    )
    assert uncorrected.toe_location_x_t_m == pytest.approx(216.89801264894433)
    assert corrected.toe_location_x_t_m == pytest.approx(144.12934726460983)


def test_scenario_d_head_branch_is_finite_and_reaches_toe_head() -> None:
    parameters = paper_parameters(L_w_m=10.0, h_w_m=15.0).model_copy(
        update={"wall_thickness_m": 40.0}
    )
    derived = compute_derived(parameters)
    L_w_bar = parameters.L_w_m / derived.x_t_no_wall_m
    h_w_bar = parameters.h_w_m / parameters.H_m
    w_bar = parameters.wall_thickness_m / derived.x_t_no_wall_m
    xh_bar = xh_dimensionless(L_w_bar, h_w_bar, derived.kappa)
    toe_bar = toe_dimensionless("d", L_w_bar, h_w_bar, w_bar, derived.kappa)

    values = [
        head_dimensionless(x, "d", parameters, derived, xh_bar)
        for x in (0.0, L_w_bar / 2.0, xh_bar, (xh_bar + toe_bar) / 2.0, toe_bar)
    ]
    assert all(math.isfinite(value) for value in values)
    toe_head = derived.phi_s_m + parameters.H_m * values[-1]
    assert toe_head == pytest.approx(derived.phi_t_m, abs=1e-9)


def test_profile_point_count_must_be_at_least_two() -> None:
    with pytest.raises(ValueError):
        run_simulation(paper_parameters(), profile_points=1)
