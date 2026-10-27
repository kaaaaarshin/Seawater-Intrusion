"""Application-wide configuration and paper-derived defaults.

All scientific defaults come from Table 2 of Sun et al. (2026).  The
analytical model itself lives in ``app.models``; this module only holds
defaults, paths and provenance metadata.
"""

from __future__ import annotations

from pathlib import Path

APP_VERSION = "1.0.0"
MODEL_VERSION = "sun2026-confined-cutoff-v1"
PAPER_TITLE = (
    "A novel analytical solution for quantifying seawater intrusion in "
    "coastal aquifers embedded with a cutoff wall"
)
PAPER_AUTHORS = "Jiazhi Sun, Wenlong Shi, Huiqiang Wu, Jie Yang, Chunhui Lu"
PAPER_JOURNAL = "Advances in Water Resources 212 (2026) 105301"
PAPER_DOI = "10.1016/j.advwatres.2026.105301"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
REFERENCE_DIR = PROJECT_ROOT / "docs" / "reference"

CASES_CSV = DATA_DIR / "simulation_cases.csv"
RESULTS_CSV = RESULTS_DIR / "simulation_results.csv"
PROFILES_CSV = RESULTS_DIR / "profiles.csv"
MANIFEST_JSON = RESULTS_DIR / "manifest.json"
DATASET_ZIP = RESULTS_DIR / "seawater_intrusion_dataset.zip"

# Table 2, Sun et al. (2026)
DEFAULT_PARAMETERS: dict[str, float] = {
    "H_m": 30.0,
    "H_s_m": 35.0,
    "K_a_m_per_day": 10.0,
    "K_w_m_per_day": 0.001,
    "wall_thickness_m": 1.0,
    "q_f_m2_per_day": 0.36,
    "rho_f_kg_per_m3": 1000.0,
    "rho_s_kg_per_m3": 1025.0,
    # Used only by the optional Pool-Carrera correction (Eq. 43).
    "alpha_T_m": 0.1,
}

WALL_LOCATIONS_M: tuple[float, ...] = (0.0, 38.0, 77.0, 115.0)
WALL_OPENING_HEIGHTS_M: tuple[float, ...] = (6.0, 12.0, 18.0, 24.0)

DEFAULT_DOMAIN_LENGTH_M = 1000.0
DEFAULT_PROFILE_POINTS = 401

CORRECTION_MODES = ("pool_carrera_flux", "none")
DEFAULT_CORRECTION_MODE = "pool_carrera_flux"

# Paper-reported toe locations used by validation.  These values are text
# values from Section 3.1 (not plot digitisation).
PAPER_REFERENCE_TOE_M: dict[str, float] = {
    "no_wall": 191.7,
    "Lw=0,hw=12": 106.0,
    "Lw=38,hw=12": 144.0,
    "Lw=77,hw=12": 181.0,
    "Lw=115,hw=12": 188.3,
}
PAPER_REFERENCE_HW_M = 12.0
PAPER_REFERENCE_TOLERANCE_M = 0.5

ASSUMPTIONS: tuple[str, ...] = (
    "Steady-state flow.",
    "Confined coastal aquifer with a sharp freshwater-seawater interface.",
    "Immiscible fluids and a static seawater phase (Ghyben-Herzberg relation).",
    "Dupuit-Forchheimer approximation with predominantly horizontal flow.",
    "Constant inland freshwater flux q_f at x = L.",
    "The cutoff wall has uniform conductivity K_w and thickness w.",
    "Local two-dimensional flow and vertical gradients near the wall are not resolved.",
    "The primary results apply the optional Pool-Carrera mixing correction (Eq. 43); "
    "the uncorrected sharp-interface toe is reported alongside it.",
)
