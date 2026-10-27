from __future__ import annotations

import pytest

from app.config import DEFAULT_PARAMETERS, PAPER_REFERENCE_TOE_M
from app.models.parameters import Parameters
from app.services.validation_service import run_validation


def test_default_validation_passes_all_checks() -> None:
    result = run_validation()
    assert result["validation_status"] == "passed"
    assert result["math_status"] == "passed"
    assert result["paper_status"] == "passed"
    assert result["total_checks"] == 14
    assert result["passed_checks"] == 14
    assert result["failed_checks"] == 0
    assert result["not_applicable_checks"] == 0


def test_paper_checks_report_reference_and_computed_values() -> None:
    result = run_validation()
    paper_checks = {
        check["check_id"]: check
        for check in result["checks"]
        if check["layer"] == "paper"
    }
    assert set(paper_checks) == {
        "paper_no_wall",
        "paper_Lw0",
        "paper_Lw38",
        "paper_Lw77",
        "paper_Lw115",
    }
    assert paper_checks["paper_no_wall"]["reference"] == PAPER_REFERENCE_TOE_M[
        "no_wall"
    ]
    assert paper_checks["paper_Lw0"]["computed"] == pytest.approx(
        106.16479288326705
    )
    assert paper_checks["paper_Lw115"]["absolute_difference"] < 0.5


def test_uncorrected_validation_marks_paper_checks_not_applicable() -> None:
    result = run_validation(correction_mode="none")
    assert result["math_status"] == "passed"
    assert result["paper_status"] == "not_applicable"
    assert result["validation_status"] == "not_applicable"
    assert result["not_applicable_checks"] == 5


def test_custom_parameters_mark_paper_checks_not_applicable() -> None:
    parameters = Parameters(
        **{**DEFAULT_PARAMETERS, "K_a_m_per_day": 5.0},
        L_w_m=0.0,
        h_w_m=12.0,
    )
    result = run_validation(parameters=parameters)
    assert result["validation_status"] == "not_applicable"
    assert all(
        check["status"] == "not_applicable"
        for check in result["checks"]
        if check["layer"] == "paper"
    )


def test_math_checks_include_expected_invariants() -> None:
    result = run_validation()
    ids = {
        check["check_id"]
        for check in result["checks"]
        if check["layer"] == "mathematical"
    }
    assert {
        "alpha_base",
        "kappa",
        "alpha_effective",
        "toe_head_condition",
        "head_continuity",
        "inland_flux_bc",
        "scenario_geometry",
        "coast_bc",
        "interface_endpoints",
    } == ids
