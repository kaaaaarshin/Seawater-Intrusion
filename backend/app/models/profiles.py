"""Profile construction for hydraulic head and interface elevation."""

from __future__ import annotations

from math import isfinite
from typing import Any

import numpy as np

from .analytical_model import CoreResult, _head_at
from .parameters import DerivedParameters, Parameters


def _region_label(
    x_m: float,
    parameters: Parameters,
    core: CoreResult,
    toe_m: float,
) -> str:
    if x_m > toe_m + 1e-7:
        return "freshwater zone (x > x_t)"
    left = parameters.L_w_m
    right = left + parameters.wall_thickness_m
    if left - 1e-9 <= x_m <= right + 1e-9:
        return "cutoff-wall region"
    return "interface zone"


def build_profiles(
    parameters: Parameters,
    derived: DerivedParameters,
    core: CoreResult,
    *,
    profile_points: int = 401,
    warnings: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build one row per x location with head and interface elevation.

    Head is defined over the whole domain.  Interface elevation is only
    defined for ``x <= x_t``; rows inland of the toe carry ``None`` rather
    than a fabricated extension.
    """

    if warnings is None:
        warnings = []
    if profile_points < 2:
        raise ValueError("profile_points must be at least 2")

    toe_m = core.toe_m
    wall_right = parameters.L_w_m + parameters.wall_thickness_m
    x_max = max(parameters.domain_length_m, wall_right, toe_m)
    if toe_m > parameters.domain_length_m + 1e-9:
        x_max = max(x_max, toe_m * 1.02, toe_m + 1.0)
        warnings.append(
            "Profile domain was extended beyond the configured L so the toe is visible."
        )

    breakpoints = [0.0, parameters.L_w_m, wall_right, toe_m, x_max]
    if core.classification.scenario_id in ("d", "e", "f") and isfinite(core.xh_m):
        breakpoints.append(core.xh_m)
    base = np.linspace(0.0, x_max, profile_points, dtype=float)
    values = np.concatenate([base, np.asarray(breakpoints, dtype=float)])
    values = values[np.isfinite(values)]
    values.sort()
    # Deduplicate after rounding to avoid duplicate chart points while keeping
    # the exact physical boundaries represented.
    x_values = sorted({round(float(v), 9) for v in values})
    x_values = [x for x in x_values if -1e-12 <= x <= x_max + 1e-9]

    profiles: list[dict[str, Any]] = []
    for x_m in x_values:
        phi = _head_at(float(x_m), parameters, derived, core)
        interface_defined = float(x_m) <= toe_m + 1e-7
        if interface_defined:
            zeta = (
                (derived.alpha_effective + 1.0) * parameters.H_s_m
                - derived.alpha_effective * phi
            )
            if abs(zeta) < 1e-8:
                zeta = 0.0
        else:
            zeta = None
        profiles.append(
            {
                "x_m": float(x_m),
                "hydraulic_head_phi_m": float(phi),
                "interface_elevation_zeta_m": None if zeta is None else float(zeta),
                "interface_defined": bool(interface_defined),
                "region": _region_label(float(x_m), parameters, core, toe_m),
            }
        )
    return profiles
