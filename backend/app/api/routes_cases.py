"""Parameter defaults, scenario definitions and latest results."""

from __future__ import annotations

from fastapi import APIRouter

from ..config import (
    ASSUMPTIONS,
    CORRECTION_MODES,
    DEFAULT_PARAMETERS,
    PAPER_DOI,
    PAPER_JOURNAL,
    PAPER_TITLE,
    WALL_LOCATIONS_M,
    WALL_OPENING_HEIGHTS_M,
)
from ..models.parameters import Parameters, compute_derived
from ..models.scenarios import scenarios_as_dicts
from ..schemas import ResultsResponse
from ..services.dataset_service import load_results

router = APIRouter(prefix="/api", tags=["cases"])


@router.get("/parameters")
def parameters() -> dict:
    base = Parameters(**DEFAULT_PARAMETERS, L_w_m=0.0, h_w_m=12.0)
    derived = compute_derived(base)
    entries = [
        {
            "key": "H_m",
            "symbol": "H",
            "value": base.H_m,
            "unit": "m",
            "description": "Confined aquifer thickness",
        },
        {
            "key": "H_s_m",
            "symbol": "H_s",
            "value": base.H_s_m,
            "unit": "m",
            "description": "Sea level / seawater depth parameter as defined by the paper",
        },
        {
            "key": "K_a_m_per_day",
            "symbol": "K_a",
            "value": base.K_a_m_per_day,
            "unit": "m/day",
            "description": "Aquifer hydraulic conductivity",
        },
        {
            "key": "K_w_m_per_day",
            "symbol": "K_w",
            "value": base.K_w_m_per_day,
            "unit": "m/day",
            "description": "Cutoff-wall hydraulic conductivity",
        },
        {
            "key": "wall_thickness_m",
            "symbol": "w",
            "value": base.wall_thickness_m,
            "unit": "m",
            "description": "Cutoff-wall thickness",
        },
        {
            "key": "q_f_m2_per_day",
            "symbol": "q_f",
            "value": base.q_f_m2_per_day,
            "unit": "m^2/day",
            "description": "Constant inland freshwater flux per unit coastline",
        },
        {
            "key": "rho_f_kg_per_m3",
            "symbol": "rho_f",
            "value": base.rho_f_kg_per_m3,
            "unit": "kg/m^3",
            "description": "Freshwater density",
        },
        {
            "key": "rho_s_kg_per_m3",
            "symbol": "rho_s",
            "value": base.rho_s_kg_per_m3,
            "unit": "kg/m^3",
            "description": "Seawater density",
        },
        {
            "key": "alpha_T_m",
            "symbol": "alpha_T",
            "value": base.alpha_T_m,
            "unit": "m",
            "description": "Transverse dispersivity used only by the optional Eq. (43) correction",
        },
        {
            "key": "domain_length_m",
            "symbol": "L",
            "value": base.domain_length_m,
            "unit": "m",
            "description": "Profile domain length; the constant-flux boundary is at x = L",
        },
    ]
    return {
        "parameters": entries,
        "derived": derived.as_dict(),
        "allowed_wall_locations_m": list(WALL_LOCATIONS_M),
        "allowed_wall_opening_heights_m": list(WALL_OPENING_HEIGHTS_M),
        "correction_modes": list(CORRECTION_MODES),
        "default_correction_mode": "pool_carrera_flux",
        "boundary_condition": (
            "Constant inland freshwater flux q_f at x = L; coastline head follows "
            "the confined-aquifer Eq. (3)."
        ),
        "assumptions": list(ASSUMPTIONS),
        "paper": {
            "title": PAPER_TITLE,
            "journal": PAPER_JOURNAL,
            "doi": PAPER_DOI,
        },
        "status_note": (
            "Generated simulations are physics-based analytical results, not field observations."
        ),
    }


@router.get("/scenarios")
def scenarios() -> dict:
    return {
        "scenarios": scenarios_as_dicts(),
        "classification_source": "Sun et al. (2026), Eq. (23), confined aquifer branch",
        "note": (
            "The 16 paper configurations for the default parameters trigger only "
            "scenarios (c) and (e). All six head/toe branches are implemented. "
            "Scenario (d) is not reachable under the strict Eq. (23) inequalities "
            "for 0 < kappa < 1 and positive wall thickness; its equations are "
            "exercised directly and its zone-2/zone-3 heads are used by scenario (e)."
        ),
    }


@router.get("/results", response_model=ResultsResponse)
def results() -> ResultsResponse:
    return ResultsResponse(**load_results())
