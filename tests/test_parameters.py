from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import DEFAULT_PARAMETERS
from app.models.parameters import Parameters, compute_derived


def paper_parameters(**overrides) -> Parameters:
    values = {**DEFAULT_PARAMETERS, "L_w_m": 0.0, "h_w_m": 12.0}
    values.update(overrides)
    return Parameters(**values)


def test_density_ratio_and_wall_ratio_follow_paper() -> None:
    parameters = paper_parameters()
    derived = compute_derived(parameters)
    assert derived.alpha_base == pytest.approx(40.0)
    assert derived.kappa == pytest.approx(1e-4)
    assert derived.gamma1_m == pytest.approx(4.694355821947745)
    assert derived.x_t_no_wall_m == pytest.approx(191.71959564551693)


def test_pool_carrera_correction_matches_equation_43() -> None:
    derived = compute_derived(paper_parameters())
    expected = 40.0 / (1.0 - (0.1 / 30.0) ** (1.0 / 6.0))
    assert derived.alpha_corrected == pytest.approx(expected)
    assert derived.alpha_effective == pytest.approx(65.19938641594091)
    assert derived.correction_factor == pytest.approx(expected / 40.0)


def test_uncorrected_mode_uses_alpha_base() -> None:
    derived = compute_derived(paper_parameters(correction_mode="none"))
    assert derived.alpha_effective == pytest.approx(40.0)
    assert derived.alpha_corrected == pytest.approx(40.0)
    assert derived.correction_factor == pytest.approx(1.0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"rho_s_kg_per_m3": 1000.0},
        {"rho_s_kg_per_m3": 990.0},
        {"K_w_m_per_day": 10.0},
        {"K_w_m_per_day": 20.0},
        {"h_w_m": 30.0},
        {"h_w_m": 40.0},
        {"L_w_m": 1000.0},
        {"L_w_m": 1001.0},
        {"alpha_T_m": 30.0},
        {"H_m": -1.0},
        {"q_f_m2_per_day": 0.0},
    ],
)
def test_invalid_physical_parameters_are_rejected(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        paper_parameters(**overrides)


def test_unknown_parameters_are_rejected() -> None:
    with pytest.raises(ValidationError):
        paper_parameters(unexpected_field=1.0)


def test_uncorrected_mode_allows_alpha_t_at_aquifer_thickness() -> None:
    parameters = paper_parameters(correction_mode="none", alpha_T_m=30.0)
    assert parameters.alpha_T_m == 30.0
