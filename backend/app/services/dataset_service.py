"""Dataset generation, CSV/manifest writing, and download helpers."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import (
    APP_VERSION,
    CASES_CSV,
    DATA_DIR,
    DATASET_ZIP,
    DEFAULT_PARAMETERS,
    MANIFEST_JSON,
    MODEL_VERSION,
    PAPER_DOI,
    PAPER_JOURNAL,
    PAPER_TITLE,
    PROFILES_CSV,
    RESULTS_CSV,
    RESULTS_DIR,
    WALL_LOCATIONS_M,
    WALL_OPENING_HEIGHTS_M,
)
from ..models.parameters import compute_derived
from ..schemas import DatasetGenerateRequest
from .simulation_service import default_batch_requests, make_case_id, run_single
from .validation_service import run_validation

CASE_COLUMNS = [
    "case_id",
    "L_w_m",
    "h_w_m",
    "H_m",
    "H_s_m",
    "K_a_m_per_day",
    "K_w_m_per_day",
    "wall_thickness_m",
    "q_f_m2_per_day",
    "rho_f_kg_per_m3",
    "rho_s_kg_per_m3",
    "alpha",
    "alpha_effective",
    "kappa",
    "correction_mode",
    "model_version",
    "generated_at",
]

RESULT_EXTRA_COLUMNS = [
    "scenario_id",
    "scenario_title",
    "scenario_description",
    "toe_location_x_t_m",
    "toe_dimensionless",
    "toe_location_uncorrected_m",
    "uncorrected_scenario_id",
    "xh_m",
    "x_t_no_wall_m",
    "head_at_inland_boundary_m",
    "status",
    "warnings",
    "error",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _base_case_row(request, result: dict[str, Any] | None, generated_at: str) -> dict[str, Any]:
    parameters = request.to_parameters()
    derived = compute_derived(parameters)
    return {
        "case_id": request.case_id or make_case_id(float(request.L_w_m), float(request.h_w_m)),
        "L_w_m": parameters.L_w_m,
        "h_w_m": parameters.h_w_m,
        "H_m": parameters.H_m,
        "H_s_m": parameters.H_s_m,
        "K_a_m_per_day": parameters.K_a_m_per_day,
        "K_w_m_per_day": parameters.K_w_m_per_day,
        "wall_thickness_m": parameters.wall_thickness_m,
        "q_f_m2_per_day": parameters.q_f_m2_per_day,
        "rho_f_kg_per_m3": parameters.rho_f_kg_per_m3,
        "rho_s_kg_per_m3": parameters.rho_s_kg_per_m3,
        "alpha": derived.alpha_base,
        "alpha_effective": derived.alpha_effective,
        "kappa": derived.kappa,
        "correction_mode": parameters.correction_mode,
        "model_version": MODEL_VERSION,
        "generated_at": generated_at,
    }


def generate_dataset(request: DatasetGenerateRequest | None = None) -> dict[str, Any]:
    """Run the 16 planned configurations and write all dataset artifacts."""

    if request is None:
        request = DatasetGenerateRequest()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = _utc_now()

    requests = default_batch_requests(
        correction_mode=request.correction_mode,
        include_profiles=True,
    )

    case_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    successful = 0

    for case_request in requests:
        case_row = _base_case_row(case_request, None, generated_at)
        try:
            result = run_single(case_request)
        except Exception as exc:
            case_rows.append(case_row)
            result_row = {**case_row, "status": "failed", "error": str(exc)}
            result_rows.append(result_row)
            errors.append(
                {
                    "case_id": case_row["case_id"],
                    "code": type(exc).__name__,
                    "message": str(exc),
                    "field": None,
                }
            )
            continue

        successful += 1
        case_rows.append(case_row)
        result_row = {
            **case_row,
            "scenario_id": result["scenario_id"],
            "scenario_title": result["scenario_title"],
            "scenario_description": result["scenario_description"],
            "toe_location_x_t_m": result["toe_location_x_t_m"],
            "toe_dimensionless": result["toe_dimensionless"],
            "toe_location_uncorrected_m": result["toe_location_uncorrected_m"],
            "uncorrected_scenario_id": result["uncorrected_scenario_id"],
            "xh_m": result["xh_m"],
            "x_t_no_wall_m": result["x_t_no_wall_m"],
            "head_at_inland_boundary_m": result.get("head_at_inland_boundary_m"),
            "status": result["status"],
            "warnings": " | ".join(result.get("warnings", [])),
            "error": "",
        }
        result_rows.append(result_row)
        for point in result.get("profiles", []):
            profile_rows.append(
                {
                    "case_id": case_row["case_id"],
                    "x_m": point["x_m"],
                    "hydraulic_head_phi_m": point["hydraulic_head_phi_m"],
                    "interface_elevation_zeta_m": point["interface_elevation_zeta_m"],
                    "interface_defined": point["interface_defined"],
                    "region": point["region"],
                    "correction_mode": result["parameters"]["correction_mode"],
                }
            )

    cases_df = pd.DataFrame(case_rows, columns=CASE_COLUMNS)
    results_df = pd.DataFrame(result_rows).reindex(
        columns=CASE_COLUMNS + RESULT_EXTRA_COLUMNS
    )
    profiles_df = pd.DataFrame(
        profile_rows,
        columns=[
            "case_id",
            "x_m",
            "hydraulic_head_phi_m",
            "interface_elevation_zeta_m",
            "interface_defined",
            "region",
            "correction_mode",
        ],
    )

    cases_df.to_csv(CASES_CSV, index=False, na_rep="")
    results_df.to_csv(RESULTS_CSV, index=False, na_rep="")
    profiles_df.to_csv(PROFILES_CSV, index=False, na_rep="")

    if request.run_validation_after:
        try:
            validation = run_validation(correction_mode=request.correction_mode)
            validation_status = validation["validation_status"]
        except Exception as exc:  # validation must not corrupt generation
            validation = {
                "validation_status": "failed",
                "error": str(exc),
            }
            validation_status = "failed"
    else:
        validation = {"validation_status": "not_run"}
        validation_status = "not_run"

    files = {
        "cases_csv": str(CASES_CSV),
        "results_csv": str(RESULTS_CSV),
        "profiles_csv": str(PROFILES_CSV),
        "manifest_json": str(MANIFEST_JSON),
    }
    manifest = {
        "generated_at": generated_at,
        "registration": "physics-based analytical simulation; not field observations",
        "app_version": APP_VERSION,
        "model_version": MODEL_VERSION,
        "paper": {
            "title": PAPER_TITLE,
            "journal": PAPER_JOURNAL,
            "doi": PAPER_DOI,
            "source_pdf": "docs/reference/Sun2026_CutoffWall.pdf",
            "algorithm_screenshot": "docs/reference/algorithm_1.jpeg",
        },
        "configuration": {
            "correction_mode": request.correction_mode,
            "wall_locations_m": list(WALL_LOCATIONS_M),
            "wall_opening_heights_m": list(WALL_OPENING_HEIGHTS_M),
            "default_parameters": DEFAULT_PARAMETERS,
        },
        "case_count": len(cases_df),
        "successful_cases": successful,
        "failed_cases": len(cases_df) - successful,
        "errors": errors,
        "validation_status": validation_status,
        "validation_summary": {
            "validation_status": validation.get("validation_status"),
            "math_status": validation.get("math_status"),
            "paper_status": validation.get("paper_status"),
            "total_checks": validation.get("total_checks"),
            "passed_checks": validation.get("passed_checks"),
            "failed_checks": validation.get("failed_checks"),
            "not_applicable_checks": validation.get("not_applicable_checks"),
        },
        "assumptions": [
            "Steady state",
            "Confined aquifer",
            "Sharp interface",
            "Constant inland freshwater flux",
            "Dupuit-Forchheimer approximation",
            "No local 2D flow resolution near the wall",
        ],
        "files": files,
        "sha256": {
            "cases_csv": _sha256(CASES_CSV),
            "results_csv": _sha256(RESULTS_CSV),
            "profiles_csv": _sha256(PROFILES_CSV),
        },
    }
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # The ZIP is rebuilt on demand by the download endpoint.  Remove a stale
    # archive so it can never be mistaken for the current dataset.
    if DATASET_ZIP.exists():
        DATASET_ZIP.unlink()

    return {
        "status": "success" if successful == len(cases_df) else "partial",
        "files": {key: str(value) for key, value in files.items()},
        "total_cases": len(cases_df),
        "successful": successful,
        "failed": len(cases_df) - successful,
        "validation_status": validation_status,
        "validation_summary": manifest["validation_summary"],
        "manifest": manifest,
        "errors": errors,
    }


def create_dataset_zip() -> Path:
    required = [CASES_CSV, RESULTS_CSV, PROFILES_CSV, MANIFEST_JSON]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "dataset files are missing; run POST /api/dataset/generate first: "
            + ", ".join(missing)
        )
    DATASET_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DATASET_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in required:
            archive.write(path, arcname=path.name)
    return DATASET_ZIP


def load_results() -> dict[str, Any]:
    if not RESULTS_CSV.exists():
        return {
            "generated": False,
            "message": "No dataset has been generated yet. Run the 16-case batch and generate the dataset.",
            "cases": [],
            "manifest": None,
        }
    df = pd.read_csv(RESULTS_CSV)
    clean = df.astype(object).where(pd.notnull(df), None)
    manifest = read_manifest()
    return {
        "generated": True,
        "message": f"Loaded {len(df)} generated cases from results/simulation_results.csv.",
        "cases": clean.to_dict(orient="records"),
        "manifest": manifest,
    }


def read_manifest() -> dict[str, Any] | None:
    if not MANIFEST_JSON.exists():
        return None
    try:
        return json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
