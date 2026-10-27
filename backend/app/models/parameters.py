"""Physical parameters and derived quantities for the confined model.

Datum and sign conventions follow Sun et al. (2026):

* x = 0 is the coastline and x increases inland.
* z = 0 is the aquifer base and z = H is the aquifer top.
* ``phi`` is hydraulic head relative to the aquifer base [L].
* ``q_f`` is the positive inland freshwater flux per unit coastline [L^2/T].

Note on alpha: Eq. (2) of the paper defines
``alpha = rho_f / (rho_s - rho_f)`` (= 40 for the paper's densities).
Algorithm 1 contains a typographical inversion of this expression; the
equation and Table 2 values are used here.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CorrectionMode = Literal["pool_carrera_flux", "none"]


class Parameters(BaseModel):
    """Validated physical parameters for one simulation configuration."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    H_m: float = Field(default=30.0, gt=0, description="Confined aquifer thickness [m]")
    H_s_m: float = Field(default=35.0, gt=0, description="Sea level / seawater depth parameter [m]")
    K_a_m_per_day: float = Field(default=10.0, gt=0, description="Aquifer hydraulic conductivity [m/day]")
    K_w_m_per_day: float = Field(default=0.001, gt=0, description="Cutoff-wall hydraulic conductivity [m/day]")
    wall_thickness_m: float = Field(default=1.0, gt=0, description="Cutoff-wall thickness w [m]")
    q_f_m2_per_day: float = Field(default=0.36, gt=0, description="Constant inland freshwater flux q_f [m^2/day]")
    rho_f_kg_per_m3: float = Field(default=1000.0, gt=0, description="Freshwater density [kg/m^3]")
    rho_s_kg_per_m3: float = Field(default=1025.0, gt=0, description="Seawater density [kg/m^3]")
    alpha_T_m: float = Field(default=0.1, ge=0, description="Transverse dispersivity used by Eq. (43) [m]")
    domain_length_m: float = Field(default=1000.0, gt=0, description="Profile domain length L [m]")

    L_w_m: float = Field(ge=0, description="Distance from coastline to the left wall edge [m]")
    h_w_m: float = Field(gt=0, description="Cutoff-wall opening height h_w [m]")
    correction_mode: CorrectionMode = Field(
        default="pool_carrera_flux",
        description="'pool_carrera_flux' applies Eq. (43); 'none' uses alpha = 40.",
    )

    @model_validator(mode="after")
    def _validate_physical_constraints(self) -> "Parameters":
        if self.rho_s_kg_per_m3 <= self.rho_f_kg_per_m3:
            raise ValueError("rho_s must be greater than rho_f")
        if self.K_w_m_per_day >= self.K_a_m_per_day:
            raise ValueError("K_w must be smaller than K_a for a low-permeability cutoff wall")
        if self.h_w_m >= self.H_m:
            raise ValueError("h_w must be smaller than the aquifer thickness H")
        if self.L_w_m + self.wall_thickness_m > self.domain_length_m:
            raise ValueError("the cutoff wall must lie inside the profile domain (L_w + w <= L)")
        if self.correction_mode == "pool_carrera_flux" and self.alpha_T_m >= self.H_m:
            raise ValueError("alpha_T must be smaller than H for the Eq. (43) correction")
        return self

    @property
    def alpha_base(self) -> float:
        """Density ratio from Eq. (2): rho_f / (rho_s - rho_f)."""
        return self.rho_f_kg_per_m3 / (self.rho_s_kg_per_m3 - self.rho_f_kg_per_m3)

    @property
    def kappa(self) -> float:
        """Wall-to-aquifer conductivity ratio K_w / K_a."""
        return self.K_w_m_per_day / self.K_a_m_per_day


@dataclass(frozen=True)
class DerivedParameters:
    """Derived coefficients and reference scales with explicit units."""

    alpha_base: float
    alpha_corrected: float
    alpha_effective: float
    correction_factor: float
    kappa: float
    gamma1_m: float
    x_t_no_wall_m: float
    phi_s_m: float
    phi_t_m: float

    def as_dict(self) -> dict[str, float]:
        return {
            "alpha_base": self.alpha_base,
            "alpha_corrected": self.alpha_corrected,
            "alpha_effective": self.alpha_effective,
            "correction_factor": self.correction_factor,
            "kappa": self.kappa,
            "gamma1_m": self.gamma1_m,
            "x_t_no_wall_m": self.x_t_no_wall_m,
            "phi_s_m": self.phi_s_m,
            "phi_t_m": self.phi_t_m,
        }


def compute_derived(parameters: Parameters, *, force_no_correction: bool = False) -> DerivedParameters:
    """Compute all derived quantities for the confined model.

    The optional correction is Eq. (43) of Sun et al. (2026):

        alpha' = alpha * [1 - (alpha_T / H)^(1/6)]^-1

    It is applied by replacing alpha with alpha' in the dimensionless
    equations, which is the interpretation that reproduces the paper's
    reported corrected toe locations.
    """

    alpha_base = parameters.alpha_base
    if force_no_correction or parameters.correction_mode == "none":
        correction_factor = 1.0
        alpha_corrected = alpha_base
    else:
        correction_factor = 1.0 / (1.0 - (parameters.alpha_T_m / parameters.H_m) ** (1.0 / 6.0))
        alpha_corrected = alpha_base * correction_factor

    alpha = alpha_corrected
    kappa = parameters.kappa
    gamma1 = 2.0 * alpha * parameters.q_f_m2_per_day / parameters.K_a_m_per_day
    if gamma1 <= 0 or not isfinite(gamma1):
        raise ValueError("derived gamma1 is not finite and positive")

    x_t_no_wall = parameters.H_m**2 / gamma1
    phi_s = (1.0 + 1.0 / alpha) * parameters.H_s_m - parameters.H_m / alpha
    phi_t = (1.0 + 1.0 / alpha) * parameters.H_s_m

    return DerivedParameters(
        alpha_base=alpha_base,
        alpha_corrected=alpha_corrected,
        alpha_effective=alpha,
        correction_factor=correction_factor,
        kappa=kappa,
        gamma1_m=gamma1,
        x_t_no_wall_m=x_t_no_wall,
        phi_s_m=phi_s,
        phi_t_m=phi_t,
    )
