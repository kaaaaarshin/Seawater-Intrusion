# Seawater Intrusion Analytical Simulator

A full-stack scientific application for steady-state seawater intrusion in a
confined coastal aquifer with a low-permeability cutoff wall. The model
implements the confined-aquifer, constant-inland-flux analytical solution from
Sun et al. (2026), generates a 16-case dataset, and visualizes hydraulic-head
and sharp-interface profiles.

> **Status:** the analytical model, API, automated validation, dataset, and
> frontend are implemented. The default validation run passes 14 of 14 checks.
> This is not a field dataset and no SEAWAT/numerical-model validation was
> performed.

## Scientific basis

Sun, J., Shi, W., Wu, H., Yang, J., and Lu, C. (2026).
“A novel analytical solution for quantifying seawater intrusion in coastal
aquifers embedded with a cutoff wall.”
*Advances in Water Resources* 212, 105301.
DOI: [10.1016/j.advwatres.2026.105301](https://doi.org/10.1016/j.advwatres.2026.105301).

Shipped source files:

- `docs/reference/Sun2026_CutoffWall.pdf`
- `docs/reference/algorithm_1.jpeg`

The implementation uses the **confined aquifer** and **constant inland
freshwater flux** branch only. Details, equation numbers, notation, and source
ambiguities are recorded in [`docs/model-notes.md`](docs/model-notes.md);
validation evidence and limitations are recorded in
[`docs/validation-notes.md`](docs/validation-notes.md).

### Key assumptions

- Steady state and a sharp freshwater–seawater interface.
- Confined aquifer, homogeneous except inside the cutoff wall.
- Static seawater phase and Ghyben–Herzberg relation.
- Dupuit–Forchheimer approximation with predominantly horizontal flow.
- Constant inland freshwater flux `q_f` at `x = L`.
- Local two-dimensional flow and dispersion near the wall are not resolved.
- The primary toe uses the optional Pool–Carrera correction from Eq. (43); the
  uncorrected sharp-interface toe is always reported alongside it.

### Source interpretation notes

- `alpha = rho_f/(rho_s - rho_f) = 40`, following Eq. (2) and Table 2. The
  supplied algorithm screenshot has an inverted expression.
- `L_w = 0` is a wall at the coastline, not a no-wall case. The no-wall case is
  a separate explicit baseline.
- On p. 8 the paper text calls panels `a2, b2, c2, d2` an 18 m wall, while the
  Fig. 4 caption defines index 2 as `h_w = 12 m`; the reported toe values match
  the `12 m` equation input. Validation uses `12 m` and documents this
  inconsistency.
- Scenario (d) is not reachable under the strict printed Eq. (23) inequalities
  for `0 < kappa < 1`; its equations are implemented and tested directly, and
  its head zones are used by scenario (e).

## Features

- FastAPI backend with validated Pydantic request/response schemas.
- Analytical head/toe solutions for scenarios (a)–(f).
- Automatic scenario classification from Eq. (23).
- Single-case wall and explicit no-wall simulations.
- 16-case batch execution with per-case status and errors.
- Generated `data/` and `results/` CSVs plus JSON manifest and ZIP download.
- Two-layer validation: mathematical invariants and paper-reference values.
- React/Vite dashboard with head/interface charts, wall/toe markers, batch
  table, validation table, assumptions, and honest loading/error/offline states.
- No hardcoded scientific results in the frontend; all displayed values come
  from backend responses.

## Repository structure

```text
.
├── backend/
│   └── app/
│       ├── api/                 FastAPI routes
│       ├── models/              parameters, equations, scenarios, profiles
│       ├── services/            simulation, dataset, validation
│       ├── utils/               structured API errors
│       ├── config.py
│       ├── main.py
│       └── schemas.py
├── data/
│   └── simulation_cases.csv     generated 16-case input dataset
├── docs/
│   ├── model-notes.md
│   ├── validation-notes.md
│   └── reference/               source PDF and algorithm screenshot
├── frontend/
│   ├── src/
│   │   ├── api/client.js
│   │   ├── components/
│   │   ├── pages/Dashboard.jsx
│   │   └── styles/global.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── results/
│   ├── simulation_results.csv
│   ├── profiles.csv
│   ├── manifest.json
│   └── seawater_intrusion_dataset.zip
├── tests/
│   ├── test_parameters.py
│   ├── test_scenarios.py
│   ├── test_analytical_model.py
│   ├── test_validation.py
│   └── test_api.py
├── README.md
├── READ_ME.txt
├── pyproject.toml
└── requirements.txt
```

## Setup and run

### Requirements

- Python 3.12 (the current environment uses Python 3.12.5).
- Node.js 20.19+ or 22.12+ and npm (the current environment uses Node 25.1.0).

### Backend

From the project root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On this macOS setup, `/opt/homebrew/bin/python3.12` failed during `ensurepip`;
`/usr/local/bin/python3.12` was used successfully to create `.venv`.

Backend URLs:

- Health: <http://127.0.0.1:8000/api/health>
- API docs: <http://127.0.0.1:8000/docs>

If port 8000 is already occupied, use another backend port and point the
frontend at it:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8050
# frontend/.env
VITE_API_BASE_URL=http://127.0.0.1:8050
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env       # optional; defaults to http://127.0.0.1:8000
npm run dev
```

Open the Vite URL, normally <http://localhost:5173>.

The API base URL is controlled by `VITE_API_BASE_URL`. The backend CORS
configuration allows the local Vite ports `5173` and `4173`.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend/model status and latest manifest validation state. |
| `GET` | `/api/parameters` | Table 2 defaults, units, allowed wall values, derived quantities. |
| `GET` | `/api/scenarios` | Six scenario definitions and Eq. (23) classification rules. |
| `POST` | `/api/simulate` | Run one wall configuration or explicit no-wall baseline. |
| `POST` | `/api/simulate/batch` | Run the 16 planned configurations or an explicit list. |
| `GET` | `/api/results` | Latest generated case rows and manifest. |
| `POST` | `/api/dataset/generate` | Regenerate CSVs, manifest, and dataset artifacts. |
| `GET` | `/api/dataset/download` | Download the generated CSV/manifest ZIP. |
| `POST` | `/api/validate` | Run mathematical and paper-reference checks. |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": "wall",
    "L_w_m": 0,
    "h_w_m": 12,
    "correction_mode": "pool_carrera_flux",
    "include_profiles": true
  }'
```

Invalid physical inputs return HTTP 422 with a structured `detail.code`,
`detail.message`, and `detail.field`.

## Tests

From the project root, with the virtual environment active:

```bash
.venv/bin/python -m pytest
```

Current result:

```text
65 passed
```

`pyproject.toml` sets `pythonpath = ["backend"]`, so no manual `PYTHONPATH` is
needed for pytest. To run the validation service directly:

```bash
PYTHONPATH=backend .venv/bin/python -c \
  "from app.services.validation_service import run_validation; \
   print(run_validation()['validation_status'])"
```

## Frontend build

```bash
cd frontend
npm run build
```

The production bundle is emitted to `frontend/dist/`.

## Dataset

The 16 primary cases are the Cartesian product:

- `L_w ∈ {0, 38, 77, 115} m`
- `h_w ∈ {6, 12, 18, 24} m`

Artifacts:

- `data/simulation_cases.csv` — input case table.
- `results/simulation_results.csv` — one row per case with scenario, toe,
  uncorrected toe, `x_h`, status, warnings, and provenance.
- `results/profiles.csv` — long-format `x`, `phi`, and `zeta` profiles.
- `results/manifest.json` — timestamp, model version, parameter source,
  assumptions, validation status, and SHA-256 hashes.
- `results/seawater_intrusion_dataset.zip` — rebuildable download bundle.

Interface elevation is `null` inland of the toe. Hydraulic head is still shown
there using the constant-flux freshwater-zone relation.

## Validation summary

Default run: **14/14 checks passed**.

| Case | Reference (m) | Computed (m) | Difference (m) |
|---|---:|---:|---:|
| No wall | 191.7 | 191.7196 | 0.0196 |
| `L_w=0`, `h_w=12` | 106.0 | 106.1648 | 0.1648 |
| `L_w=38`, `h_w=12` | 144.0 | 144.1293 | 0.1293 |
| `L_w=77`, `h_w=12` | 181.0 | 181.1518 | 0.1518 |
| `L_w=115`, `h_w=12` | 188.3 | 188.4182 | 0.1182 |

Tolerance: `0.5 m`, based on the precision of the text-reported values. The
mathematical checks additionally cover the coast condition, toe head, head
continuity, constant flux, interface endpoints, derived parameters, and scenario
geometry.

## Limitations

- No numerical groundwater model, field data, or transport simulation was used.
- The analytical model is steady state, sharp interface, and confined-aquifer
  only.
- Local flow near the wall and mixing/dispersion are not resolved, apart from
  the optional Pool–Carrera correction.
- Scenario (d) is documented as unreachable under the printed Eq. (23)
  conditions; this is a source-condition limitation, not a hidden fallback.
- The paper text/caption/equation `h_w` inconsistency is documented rather than
  silently forced to match.
