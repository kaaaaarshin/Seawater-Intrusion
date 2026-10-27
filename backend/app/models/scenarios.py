"""Scenario definitions and classification for the confined aquifer.

The classification uses the dimensionless limiting conditions in Eq. (23)
of Sun et al. (2026).  Dimensionless variables follow Eq. (8):

    L_w_bar = L_w / x_t^a,  w_bar = w / x_t^a,
    h_w_bar = h_w / H,      kappa = K_w / K_a

where ``x_t^a = H^2 / gamma1`` is the no-wall interface toe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite, sqrt
from typing import Any

from .parameters import DerivedParameters, Parameters


class ScenarioClassificationError(ValueError):
    """Raised when no paper scenario can be assigned to a configuration."""


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    title: str
    description: str
    condition_text: str


SCENARIO_DEFINITIONS: dict[str, ScenarioDefinition] = {
    "a": ScenarioDefinition(
        "a",
        "Wall inland of the initial interface toe",
        "The cutoff wall is constructed further inland than the interface toe without a wall.",
        "1 <= L_w_bar",
    ),
    "b": ScenarioDefinition(
        "b",
        "Interface toe beneath the wall",
        "The wall opening is above the interface at L_w, and the interface toe lies beneath the wall thickness.",
        "0 < 1 - sqrt(L_w_bar) <= h_w_bar < upper_b",
    ),
    "c": ScenarioDefinition(
        "c",
        "Interface toe inland of the wall",
        "The wall opening is above the interface at L_w, and the interface toe moves inland of L_w + w.",
        "0 < max(1 - sqrt(L_w_bar), upper_b) <= h_w_bar < 1",
    ),
    "d": ScenarioDefinition(
        "d",
        "Interface enters the wall; toe between L_w and L_w + w",
        "The interface enters the cutoff wall, exits at x_h, and its toe remains beneath the wall thickness.",
        "0 < 1 - sqrt(L_w_bar + w_bar/kappa) <= h_w_bar < lower_d_upper",
    ),
    "e": ScenarioDefinition(
        "e",
        "Interface enters the wall; toe inland of the wall",
        "The interface enters the cutoff wall at x_h and its toe lies inland of L_w + w.",
        "0 < max(1 - sqrt(L_w_bar + w_bar/kappa), lower_d_upper) <= h_w_bar < 1 - sqrt(L_w_bar)",
    ),
    "f": ScenarioDefinition(
        "f",
        "Interface exits at the wall's inland edge",
        "The interface enters the wall and exits at the right boundary L_w + w.",
        "0 < h_w_bar < 1 - sqrt(L_w_bar + w_bar/kappa)",
    ),
}


@dataclass
class ClassificationResult:
    scenario_id: str
    definition: ScenarioDefinition
    dimensionless: dict[str, float | None]
    all_matches: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _safe_sqrt(value: float) -> float | None:
    if value < -1e-12:
        return None
    return sqrt(max(0.0, value))


def classify_dimensionless(
    L_w_bar: float,
    h_w_bar: float,
    w_bar: float,
    kappa: float,
) -> ClassificationResult:
    """Classify a dimensionless configuration using Eq. (23)."""

    if not all(isfinite(v) for v in (L_w_bar, h_w_bar, w_bar, kappa)):
        raise ScenarioClassificationError("dimensionless inputs must be finite")
    if kappa <= 0 or kappa >= 1:
        raise ScenarioClassificationError("kappa must satisfy 0 < kappa < 1")

    sqrt_Lw = _safe_sqrt(L_w_bar)
    sqrt_ratio = _safe_sqrt(L_w_bar + w_bar / kappa)
    sqrt_term_2 = _safe_sqrt((kappa * (L_w_bar - 1.0) + w_bar) / (1.0 - kappa))

    if sqrt_Lw is None or sqrt_ratio is None:
        raise ScenarioClassificationError("invalid dimensionless square-root argument")

    lower_bc = 1.0 - sqrt_Lw
    denominator_b = 2.0 * (kappa - 1.0) * (sqrt_Lw - 1.0)
    upper_b = None
    if abs(denominator_b) > 1e-14:
        upper_b = 1.0 + (L_w_bar + w_bar - 1.0) / denominator_b

    lower_d = 1.0 - sqrt_ratio
    upper_d = None
    if sqrt_term_2 is not None:
        upper_d = min(lower_bc, sqrt_term_2)

    e_lower_candidates = [lower_d]
    if sqrt_term_2 is not None:
        e_lower_candidates.append(sqrt_term_2)
    e_lower = max(e_lower_candidates)

    flags: dict[str, bool] = {
        "a": L_w_bar >= 1.0,
        "b": bool(
            upper_b is not None
            and 0.0 < lower_bc <= h_w_bar < upper_b
        ),
        "c": bool(
            upper_b is not None
            and 0.0 < max(lower_bc, upper_b) <= h_w_bar < 1.0
        ),
        "d": bool(
            upper_d is not None
            and 0.0 < lower_d <= h_w_bar < upper_d
        ),
        "e": bool(
            0.0 < e_lower <= h_w_bar < lower_bc
        ),
        "f": bool(
            0.0 < h_w_bar < lower_d
        ),
    }

    matches = [sid for sid in ("a", "b", "c", "d", "e", "f") if flags[sid]]
    if not matches:
        raise ScenarioClassificationError(
            "no Eq. (23) scenario matches the configuration: "
            f"L_w_bar={L_w_bar:.8g}, h_w_bar={h_w_bar:.8g}, "
            f"w_bar={w_bar:.8g}, kappa={kappa:.8g}"
        )

    warnings: list[str] = []
    if len(matches) > 1:
        warnings.append(
            "Configuration lies on a scenario boundary; multiple Eq. (23) "
            f"conditions matched: {', '.join(matches)}. The first in paper order was used."
        )
    scenario_id = matches[0]
    dimensionless: dict[str, float | None] = {
        "L_w_bar": L_w_bar,
        "h_w_bar": h_w_bar,
        "w_bar": w_bar,
        "kappa": kappa,
        "sqrt_L_w_bar": sqrt_Lw,
        "lower_bc": lower_bc,
        "upper_b": upper_b,
        "lower_d": lower_d,
        "upper_d": upper_d,
        "e_lower": e_lower,
    }
    return ClassificationResult(
        scenario_id=scenario_id,
        definition=SCENARIO_DEFINITIONS[scenario_id],
        dimensionless=dimensionless,
        all_matches=matches,
        warnings=warnings,
    )


def classify_scenario(parameters: Parameters, derived: DerivedParameters) -> ClassificationResult:
    """Classify a dimensional configuration from Eq. (23)."""

    L_w_bar = parameters.L_w_m / derived.x_t_no_wall_m
    h_w_bar = parameters.h_w_m / parameters.H_m
    w_bar = parameters.wall_thickness_m / derived.x_t_no_wall_m
    return classify_dimensionless(L_w_bar, h_w_bar, w_bar, derived.kappa)


def scenarios_as_dicts() -> list[dict[str, Any]]:
    """Return the six scenario definitions suitable for JSON responses."""

    return [
        {
            "scenario_id": item.scenario_id,
            "title": item.title,
            "description": item.description,
            "condition_text": item.condition_text,
        }
        for item in SCENARIO_DEFINITIONS.values()
    ]
