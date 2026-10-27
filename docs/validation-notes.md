# Validation notes

## What is validated

Validation has two independent layers:

1. **Mathematical/implementation checks** for derived parameters, boundary
   conditions, head continuity, interface endpoint conditions, scenario
   geometry, and finite outputs.
2. **Paper-reference checks** comparing corrected toe locations with values
   reported in Sun et al. (2026), Section 3.1.

The API keeps these layers separate in the response (`math_status`,
`paper_status`, and `validation_status`). A generated dataset is not labelled
validated merely because the CSV files were written.

## Current result

The default validation run reports:

```text
validation_status = passed
math_status       = passed
paper_status      = passed
total_checks      = 14
passed_checks     = 14
failed_checks     = 0
not_applicable    = 0
```

The 14 checks comprise 9 mathematical checks and 5 paper-reference checks.

## Paper comparisons

Reference values are text-reported values from the paper. The tolerance is
`0.5 m`, chosen to accommodate the precision of the reported values. These are
not plot-digitized points.

| Case | Paper reference (m) | Computed (m) | Absolute difference (m) |
|---|---:|---:|---:|
| No wall | 191.7 | 191.71959564551693 | 0.0196 |
| `L_w = 0 m`, `h_w = 12 m` | 106.0 | 106.16479288326705 | 0.1648 |
| `L_w = 38 m`, `h_w = 12 m` | 144.0 | 144.12934726460983 | 0.1293 |
| `L_w = 77 m`, `h_w = 12 m` | 181.0 | 181.15183693633213 | 0.1518 |
| `L_w = 115 m`, `h_w = 12 m` | 188.3 | 188.41823978807457 | 0.1182 |

The no-wall value is the explicit scenario (a) baseline. The wall cases use the
Pool–Carrera correction from Eq. (43); the uncorrected `alpha = 40` toe is
reported separately and is not expected to match the paper’s corrected values.

### Important source note

On p. 8 the paper text calls panels `a2, b2, c2, d2` an 18 m cutoff-wall case,
but the Fig. 4 caption on the same page defines indices `1–4` as
`h_w = 6, 12, 18, 24 m`; index `2` is therefore `12 m`. The reported toe values
`106.0, 144.0, 181.0, 188.3 m` are reproduced with `h_w = 12 m`. The
application validates those `12 m` cases and states this explicitly in the
check notes. The dataset still includes all four planned opening heights
(`6, 12, 18, 24 m`).

## Mathematical checks

- `alpha = rho_f/(rho_s - rho_f) = 40`.
- `kappa = K_w/K_a = 1e-4` for the paper parameters.
- Effective alpha matches the selected correction mode.
- `phi(x_t) = (1 + 1/alpha) H_s` over all 16 paper configurations.
- Head continuity at `L_w`, `L_w + w`, and `x_h` where applicable.
- Constant inland flux `K_a H dphi/dx = q_f`.
- Scenario geometry is consistent with the assigned scenario.
- Coast condition `phi(0) = (1 + 1/alpha) H_s - H/alpha`.
- Interface endpoints `zeta(0) = H` and `zeta(x_t) = 0`.

The head-continuity check uses a `1e-11` dimensionless offset around each
boundary. This avoids mistaking the steep but finite square-root derivative for
a discontinuity when `kappa = 1e-4`; the resulting maximum head jump over the
16 cases is below `2.3e-7 m`, well within the `1e-6 m` tolerance.

## Scenario coverage

- The 16 paper configurations classify as scenarios **(c)** and **(e)** only.
- All six head/toe branches are implemented.
- Scenario **(d)** is not reachable under the strict printed Eq. (23)
  inequalities for `0 < kappa < 1` and `w > 0`; see
  `docs/model-notes.md` for the proof. Its equations are tested directly and
  its zone-2/zone-3 heads are exercised by scenario (e).
- Representative synthetic configurations exercise scenarios (a), (b), (c),
  (e), and (f) through the classifier.

## What is not validated

- No SEAWAT, MODFLOW, or other numerical groundwater simulation was run.
- No field observations are used.
- No parameter calibration or uncertainty analysis was performed.
- Transient behaviour, dispersion, and local two-dimensional flow near the wall
  are outside the sharp-interface analytical scope.

These limitations are also displayed in the frontend and recorded in the
dataset manifest.

## Reproduce the checks

From the project root:

```bash
.venv/bin/python -m pytest
```

To run only the validation service:

```bash
PYTHONPATH=backend .venv/bin/python -c \
  "from app.services.validation_service import run_validation; \
   print(run_validation()['validation_status'])"
```

Or call the API:

```bash
curl -X POST http://127.0.0.1:8000/api/validate \
  -H 'Content-Type: application/json' \
  -d '{}'
```

The generated manifest at `results/manifest.json` records the validation status,
check counts, parameter source, model version, and input-file hashes.
