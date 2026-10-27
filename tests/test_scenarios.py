from __future__ import annotations

import math

import pytest

from app.config import DEFAULT_PARAMETERS, WALL_LOCATIONS_M, WALL_OPENING_HEIGHTS_M
from app.models.analytical_model import compute_core, toe_dimensionless
from app.models.parameters import Parameters, compute_derived
from app.models.scenarios import (
    ScenarioClassificationError,
    classify_dimensionless,
    classify_scenario,
)


def paper_parameters(L_w_m: float, h_w_m: float) -> Parameters:
    return Parameters(
        **DEFAULT_PARAMETERS,
        L_w_m=L_w_m,
        h_w_m=h_w_m,
        correction_mode="pool_carrera_flux",
    )


@pytest.mark.parametrize(
    ("expected", "L_w_bar", "h_w_bar", "w_bar", "kappa"),
    [
        ("a", 1.2, 0.5, 0.01, 0.1),
        ("b", 0.99, 0.5, 0.01, 0.1),
        ("c", 0.8, 0.5, 0.01, 0.1),
        ("e", 0.5, 0.26, 0.01, 0.1),
        ("f", 0.5, 0.1, 0.01, 0.1),
    ],
)
def test_representative_scenarios(
    expected: str,
    L_w_bar: float,
    h_w_bar: float,
    w_bar: float,
    kappa: float,
) -> None:
    result = classify_dimensionless(L_w_bar, h_w_bar, w_bar, kappa)
    assert result.scenario_id == expected
    assert result.all_matches[0] == expected


def test_all_16_paper_cases_classify_as_c_or_e() -> None:
    scenarios = set()
    for L_w in WALL_LOCATIONS_M:
        for h_w in WALL_OPENING_HEIGHTS_M:
            parameters = paper_parameters(L_w, h_w)
            derived = compute_derived(parameters)
            core = compute_core(parameters, derived)
            scenarios.add(core.classification.scenario_id)
            assert core.classification.scenario_id in {"c", "e"}
    assert scenarios == {"c", "e"}


def test_scenario_d_is_not_reachable_under_eq_23() -> None:
    for L_w_bar in (0.01, 0.1, 0.5, 0.9, 0.99):
        for w_bar in (0.001, 0.01, 0.1, 0.5):
            for kappa in (0.001, 0.01, 0.1, 0.5):
                for h_w_bar in (0.01, 0.1, 0.25, 0.5, 0.9):
                    try:
                        result = classify_dimensionless(
                            L_w_bar, h_w_bar, w_bar, kappa
                        )
                    except ScenarioClassificationError:
                        continue
                    assert "d" not in result.all_matches


def test_scenario_d_equations_are_implemented() -> None:
    parameters = paper_parameters(10.0, 15.0).model_copy(
        update={"wall_thickness_m": 40.0}
    )
    derived = compute_derived(parameters)
    L_w_bar = parameters.L_w_m / derived.x_t_no_wall_m
    h_w_bar = parameters.h_w_m / parameters.H_m
    w_bar = parameters.wall_thickness_m / derived.x_t_no_wall_m
    toe = toe_dimensionless("d", L_w_bar, h_w_bar, w_bar, derived.kappa)
    assert math.isfinite(toe)
    assert toe == pytest.approx(0.30222929318183944)


@pytest.mark.parametrize(("kappa"), [0.0, -0.1, 1.0, 1.1])
def test_invalid_kappa_is_rejected(kappa: float) -> None:
    with pytest.raises(ScenarioClassificationError):
        classify_dimensionless(0.5, 0.3, 0.01, kappa)


def test_non_finite_inputs_are_rejected() -> None:
    with pytest.raises(ScenarioClassificationError):
        classify_dimensionless(float("nan"), 0.3, 0.01, 0.1)


def test_dimensional_classification_matches_dimensionless() -> None:
    parameters = paper_parameters(0.0, 12.0)
    derived = compute_derived(parameters)
    result = classify_scenario(parameters, derived)
    assert result.scenario_id == "e"
    assert result.dimensionless["L_w_bar"] == pytest.approx(0.0)
    assert result.dimensionless["h_w_bar"] == pytest.approx(0.4)
