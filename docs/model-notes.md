# Model notes: confined aquifer with a cutoff wall

## Source

- Sun, J., Shi, W., Wu, H., Yang, J., and Lu, C. (2026).
  “A novel analytical solution for quantifying seawater intrusion in coastal
  aquifers embedded with a cutoff wall.”
  *Advances in Water Resources* 212, 105301.
  DOI: `10.1016/j.advwatres.2026.105301`.
- Local PDF: `docs/reference/Sun2026_CutoffWall.pdf`.
- Algorithm screenshot supplied with the project: `docs/reference/algorithm_1.jpeg`.
- Implemented branch: confined aquifer, constant inland freshwater flux `q_f`.
  The unconfined and constant-head branches are out of scope.

### Page map used for transcription

| Source item | PDF page |
|---|---:|
| Governing equations and boundary conditions, Eqs. (1)–(4) | 3 |
| Continuity, toe relation, and interface elevation, Eqs. (5)–(7) | 4 |
| Dimensionless definitions, Eq. (8) | 4 |
| Confined head equations, Eqs. (9)–(16) | 4–5 |
| Confined toe equations, Eqs. (17)–(22) | 5 |
| Scenario conditions, Eq. (23) | 5 |
| Algorithm 1 | 6 |
| Table 2 and Pool–Carrera correction, Eq. (43) | 7 |
| Reported toe values and Fig. 4 discussion | 8 |

## Scope and sign conventions

- Steady state, sharp freshwater–seawater interface, static seawater phase.
- `x = 0` at the coastline, increasing inland.
- `z = 0` at the aquifer base, `z = H` at the aquifer top.
- `phi` is hydraulic head relative to the aquifer base, in metres.
- `q_f > 0` is the inland freshwater flux per unit coastline, in m²/day.
- The aquifer is homogeneous except inside the cutoff wall.
- The wall occupies `L_w <= x <= L_w + w` and has conductivity `K_w << K_a`.
- The inland boundary at `x = L` is constant flux:
  `K_a H dphi/dx = q_f` in the freshwater zone.
- The coastal boundary follows the paper’s confined-aquifer condition,
  not an unconfined sea-level condition.

## Parameters

Table 2 values used by the application:

| Symbol | Meaning | Value | Unit |
|---|---|---:|---|
| `H` | Aquifer thickness | 30 | m |
| `H_s` | Sea level / seawater-depth parameter | 35 | m |
| `K_a` | Aquifer conductivity | 10 | m/day |
| `K_w` | Wall conductivity | 0.001 | m/day |
| `w` | Wall thickness | 1 | m |
| `q_f` | Constant inland flux | 0.36 | m²/day |
| `rho_f` | Freshwater density | 1000 | kg/m³ |
| `rho_s` | Seawater density | 1025 | kg/m³ |
| `alpha_T` | Transverse dispersivity for Eq. (43) | 0.1 | m |

Derived:

- `alpha = rho_f / (rho_s - rho_f) = 40`.
- `kappa = K_w / K_a = 1e-4`.
- `L_w` values: `0, 38, 77, 115 m`.
- `h_w` values: `6, 12, 18, 24 m`.

## Dimensionless variables (Eq. 8)

`x_t^a = H² / gamma1`, with `gamma1 = 2 alpha q_f / K_a`.

```text
x_bar      = x / x_t^a
L_w_bar    = L_w / x_t^a
w_bar      = w / x_t^a
h_w_bar    = h_w / H
beta1      = (1 - h_w_bar)(1 - kappa)
lambda1    = beta1 - sqrt(L_w_bar)
```

## Head solution (Eqs. 9–16)

The returned dimensionless head is `phi_bar = (phi - phi_s)/H`.

```text
phi_s  = (1 + 1/alpha) H_s - H/alpha          coast condition, Eq. (3)

phi_a  = sqrt(x_bar) / alpha                  Eq. (9)
phi_b2 = [sqrt(x_bar + beta1(beta1 - 2 sqrt(L_w_bar))) + beta1] / alpha
                                               Eq. (10)
phi_c3 = sqrt(x_bar + 2 beta1 lambda1
              + 2 beta1 sqrt(lambda1² + w_bar)) / alpha
                                               Eq. (12)
phi_d2 = sqrt((x_bar - (1 - kappa)L_w_bar)/kappa) / alpha
                                               Eq. (14), wall zone 2
phi_d3 = [sqrt(x_bar - kappa beta1²/(1 - kappa)
               - (1 - kappa)L_w_bar) + beta1] / alpha
                                               Eq. (14), zone 3
phi_e4 = sqrt(x_bar - (1 - kappa)L_w_bar
              + beta1((1 - 2 kappa)/(1 - kappa) beta1
              + 2 sqrt(kappa L_w_bar + w_bar
                       - kappa beta1²/(1 - kappa)))) / alpha
                                               Eq. (15)
phi_f3 = sqrt(x_bar - (1 - 1/kappa)w_bar) / alpha
                                               Eq. (16)
```

The wall-intersection location is

```text
x_h_bar = L_w_bar(1 - kappa) + kappa(1 - h_w_bar)²      Eq. (A25)
```

Piecewise regions are selected from the scenario assigned by Eq. (23). The
implementation checks head continuity numerically at each sub-zone boundary.

## Toe solution (Eqs. 17–22)

```text
(a) x_t_bar = 1
(b) x_t_bar = 1 - 2 beta1(1 - sqrt(L_w_bar))
(c) x_t_bar = 1 - 2 beta1(lambda1 + sqrt(lambda1² + w_bar))
(d) x_t_bar = (h_w_bar² + L_w_bar)(1 - kappa) + kappa
(e) x_t_bar = (3 - 2 kappa)kappa
              - [2 beta1 sqrt(kappa L_w_bar + w_bar
                              - beta1² kappa/(1 - kappa))
              - h_w_bar(2 - h_w_bar)(1 - kappa)(1 - 2 kappa)
              - (1 - kappa)L_w_bar]
(f) x_t_bar = 1 + w_bar(1 - 1/kappa)
```

Dimensional recovery:

```text
x_t  = x_t_bar x_t^a
zeta = (1 + alpha) H_s - alpha phi
```

The primary profile uses the corrected `alpha` from Eq. (43). The toe obtained
with the uncorrected `alpha = 40` is always reported separately for comparison.

## Scenario conditions (Eq. 23)

The implementation follows the strict inequalities in the paper:

```text
lower_bc = 1 - sqrt(L_w_bar)
upper_b  = 1 + (L_w_bar + w_bar - 1)
              / [2(kappa - 1)(sqrt(L_w_bar) - 1)]
lower_d  = 1 - sqrt(L_w_bar + w_bar/kappa)
term_2   = sqrt((kappa(L_w_bar - 1) + w_bar)/(1 - kappa))
upper_d  = min(lower_bc, term_2)

(a) L_w_bar >= 1
(b) 0 < lower_bc <= h_w_bar < upper_b
(c) 0 < max(lower_bc, upper_b) <= h_w_bar < 1
(d) 0 < lower_d <= h_w_bar < upper_d
(e) 0 < max(lower_d, term_2) <= h_w_bar < lower_bc
(f) 0 < h_w_bar < lower_d
```

### Scenario (d) reachability

The strict scenario (d) inequalities are mutually exclusive for
`0 < kappa < 1`, `w_bar > 0`:

- `0 < 1 - sqrt(L_w_bar + w_bar/kappa)` requires
  `L_w_bar + w_bar/kappa < 1`.
- A real `term_2` requires `kappa(L_w_bar - 1) + w_bar >= 0`, which is
  equivalent to `L_w_bar + w_bar/kappa >= 1`.

Therefore scenario (d) is not returned by the classifier for physically valid
parameters. This is a property of the printed Eq. (23) conditions, not a
silently simplified classification rule. The scenario (d) head/toe equations
are nevertheless implemented and tested directly; the zone-2 and zone-3 head
expressions are used by scenario (e). This limitation is exposed in the API
scenario metadata and in the frontend.

## Pool–Carrera correction (Eq. 43)

```text
alpha' = alpha [1 - (alpha_T/H)^(1/6)]^-1
```

For the paper parameters, `alpha' = 65.19938641594091`. Replacement of `alpha`
by `alpha'` in the dimensionless equations reproduces the paper’s reported toe
locations. The uncorrected sharp-interface solutions use `alpha = 40`.

The project treats the correction as an optional result mode. It does not
perform a numerical transport simulation.

## No-wall baseline

`L_w = 0` is a cutoff wall at the coastline, not a no-wall case. The explicit
no-wall baseline uses scenario (a), whose interface toe is independent of wall
geometry:

```text
x_t = x_t^a = H²/gamma1
```

It is implemented as a separate API mode (`mode = "no_wall"`) and labelled
accordingly in the frontend.

## Head inland of the toe

The interface elevation is undefined inland of the toe, so the profile CSV
stores `null` for `interface_elevation_zeta_m` there. The hydraulic head is
still defined. For `x > x_t` the implementation uses the constant-flux
freshwater-zone relation

```text
phi(x) = phi_t + (q_f/(K_a H))(x - x_t)
```

This is documented in API metadata and is not presented as an interface curve.

## Source ambiguities and decisions

1. **Algorithm 1 alpha inversion.** The supplied algorithm screenshot writes
   an inverted density-ratio expression. Eq. (2) and Table 2 both give
   `alpha = rho_f/(rho_s - rho_f) = 40`; Eq. (2) is used.
2. **`h_w = 12 m` versus text “18 m”.** On p. 8 the paper text calls panels
   `a2, b2, c2, d2` an 18 m cutoff-wall case, but the Fig. 4 caption on the same
   page defines indices `1–4` as `h_w = 6, 12, 18, 24 m`; index `2` is therefore
   `12 m`. The reported toe values `106.0, 144.0, 181.0, 188.3 m` are reproduced
   with `h_w = 12 m`. Validation uses `12 m` and records the inconsistency.
3. **Reported toe values.** The values `191.7, 106.0, 144.0, 181.0, 188.3 m`
   are treated as text-reported reference values, not plot-digitized data.
4. **Scenario (d).** As shown above, the printed inequalities are not
   simultaneously satisfiable; the equations are implemented but the branch is
   not reported as reachable.
5. **No SEAWAT validation.** The project validates analytical invariants and
   reproduces paper-reported toe locations. It does not claim numerical-model
   or field validation.

## Implementation map

- Parameters and derived quantities: `backend/app/models/parameters.py`.
- Scenario classification: `backend/app/models/scenarios.py`.
- Head/toe equations and simulation orchestration: `backend/app/models/analytical_model.py`.
- Profiles and defined-domain handling: `backend/app/models/profiles.py`.
- Mathematical/paper validation: `backend/app/services/validation_service.py`.
- Dataset generation and manifest: `backend/app/services/dataset_service.py`.
