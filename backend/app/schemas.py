"""Pydantic request and response schemas for the API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import (
    DEFAULT_CORRECTION_MODE,
    DEFAULT_DOMAIN_LENGTH_M,
    DEFAULT_PROFILE_POINTS,
    DEFAULT_PARAMETERS,
)
from .models.parameters import Parameters


class FixedParameterInputs(BaseModel):
    """Common fixed physical parameters, all optional for API clients."""

    model_config = ConfigDict(extra="forbid")

    H_m: float = Field(default=DEFAULT_PARAMETERS["H_m"], gt=0)
    H_s_m: float = Field(default=DEFAULT_PARAMETERS["H_s_m"], gt=0)
    K_a_m_per_day: float = Field(default=DEFAULT_PARAMETERS["K_a_m_per_day"], gt=0)
    K_w_m_per_day: float = Field(default=DEFAULT_PARAMETERS["K_w_m_per_day"], gt=0)
    wall_thickness_m: float = Field(default=DEFAULT_PARAMETERS["wall_thickness_m"], gt=0)
    q_f_m2_per_day: float = Field(default=DEFAULT_PARAMETERS["q_f_m2_per_day"], gt=0)
    rho_f_kg_per_m3: float = Field(default=DEFAULT_PARAMETERS["rho_f_kg_per_m3"], gt=0)
    rho_s_kg_per_m3: float = Field(default=DEFAULT_PARAMETERS["rho_s_kg_per_m3"], gt=0)
    alpha_T_m: float = Field(default=DEFAULT_PARAMETERS["alpha_T_m"], ge=0)
    domain_length_m: float = Field(default=DEFAULT_DOMAIN_LENGTH_M, gt=0)


class SimulationRequest(FixedParameterInputs):
    """One single-case simulation request."""

    mode: Literal["wall", "no_wall"] = "wall"
    L_w_m: float | None = Field(default=None, ge=0)
    h_w_m: float | None = Field(default=None, gt=0)
    correction_mode: Literal["pool_carrera_flux", "none"] = DEFAULT_CORRECTION_MODE
    include_profiles: bool = True
    profile_points: int = Field(default=DEFAULT_PROFILE_POINTS, ge=2, le=5000)
    case_id: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _require_wall_inputs(self) -> "SimulationRequest":
        if self.mode == "wall":
            if self.L_w_m is None or self.h_w_m is None:
                raise ValueError("L_w_m and h_w_m are required when mode='wall'")
        return self

    def to_parameters(self) -> Parameters:
        fixed = self.model_dump(
            include=set(FixedParameterInputs.model_fields),
        )
        if self.mode == "wall":
            return Parameters(
                **fixed,
                L_w_m=float(self.L_w_m),
                h_w_m=float(self.h_w_m),
                correction_mode=self.correction_mode,
            )
        # A no-wall baseline still needs valid placeholder geometry for the
        # Parameters model; run_no_wall_baseline replaces it with an explicit
        # wall-outside-the-domain geometry.
        return Parameters(
            **fixed,
            L_w_m=0.0,
            h_w_m=min(1.0, 0.5 * fixed["H_m"]),
            correction_mode=self.correction_mode,
        )


class BatchRequest(BaseModel):
    """Run the default 16-case batch or an explicit configuration list."""

    model_config = ConfigDict(extra="forbid")

    configurations: list[SimulationRequest] | None = None
    correction_mode: Literal["pool_carrera_flux", "none"] = DEFAULT_CORRECTION_MODE
    include_profiles: bool = False


class ValidationRequest(BaseModel):
    """Validation always uses the paper's Table 2 parameter set."""

    model_config = ConfigDict(extra="forbid")

    correction_mode: Literal["pool_carrera_flux", "none"] = DEFAULT_CORRECTION_MODE


class DatasetGenerateRequest(BaseModel):
    """Request to generate the 16-case dataset."""

    model_config = ConfigDict(extra="forbid")

    correction_mode: Literal["pool_carrera_flux", "none"] = DEFAULT_CORRECTION_MODE
    run_validation_after: bool = True


class ProfilePoint(BaseModel):
    x_m: float
    hydraulic_head_phi_m: float
    interface_elevation_zeta_m: float | None
    interface_defined: bool
    region: str


class SimulationResponse(BaseModel):
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
    profiles: list[ProfilePoint] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    parameters: dict[str, Any]
    derived: dict[str, Any]
    classification: dict[str, Any]
    metadata: dict[str, Any]


class SimulationError(BaseModel):
    case_id: str | None = None
    code: str
    message: str
    field: str | None = None


class BatchCase(BaseModel):
    case_id: str
    L_w_m: float | None
    h_w_m: float | None
    scenario_id: str | None = None
    scenario_title: str | None = None
    toe_location_x_t_m: float | None = None
    toe_location_uncorrected_m: float | None = None
    xh_m: float | None = None
    status: str
    warnings: list[str] = Field(default_factory=list)
    error: SimulationError | None = None


class BatchResponse(BaseModel):
    status: str
    total: int
    successful: int
    failed: int
    cases: list[BatchCase]
    metadata: dict[str, Any]


class ValidationCheck(BaseModel):
    check_id: str
    layer: Literal["mathematical", "paper"]
    name: str
    status: Literal["passed", "failed", "not_applicable", "not_run"]
    reference: float | str | None = None
    computed: float | str | None = None
    absolute_difference: float | None = None
    relative_difference: float | None = None
    tolerance: float | None = None
    units: str | None = None
    source: str
    notes: str | None = None


class ValidationResponse(BaseModel):
    validation_status: Literal["passed", "failed", "not_applicable", "not_run"]
    math_status: Literal["passed", "failed", "not_applicable", "not_run"]
    paper_status: Literal["passed", "failed", "not_applicable", "not_run"]
    total_checks: int
    passed_checks: int
    failed_checks: int
    not_applicable_checks: int
    checks: list[ValidationCheck]
    metadata: dict[str, Any]


class DatasetGenerateResponse(BaseModel):
    status: str
    files: dict[str, str]
    total_cases: int
    successful: int
    failed: int
    validation_status: Literal["passed", "failed", "not_applicable", "not_run"]
    validation_summary: dict[str, Any]
    manifest: dict[str, Any]
    errors: list[SimulationError] = Field(default_factory=list)


class ResultsResponse(BaseModel):
    generated: bool
    message: str
    cases: list[dict[str, Any]] = Field(default_factory=list)
    manifest: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    app_version: str
    model_version: str
    model_loaded: bool
    validated: bool
    validation_status: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDetail
