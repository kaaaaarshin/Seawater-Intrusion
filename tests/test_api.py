from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def generated_dataset(client: TestClient) -> dict:
    response = client.post("/api/dataset/generate", json={})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    return body


def test_root_and_health(client: TestClient, generated_dataset: dict) -> None:
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["docs"] == "/docs"

    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["validated"] is True
    assert body["validation_status"] == "passed"


def test_parameters_endpoint(client: TestClient) -> None:
    response = client.get("/api/parameters")
    assert response.status_code == 200
    body = response.json()
    assert body["derived"]["alpha_base"] == pytest.approx(40.0)
    assert body["derived"]["alpha_effective"] == pytest.approx(65.19938641594091)
    assert body["paper"]["doi"] == "10.1016/j.advwatres.2026.105301"
    assert len(body["parameters"]) == 10
    assert body["allowed_wall_locations_m"] == [0.0, 38.0, 77.0, 115.0]


def test_scenarios_endpoint(client: TestClient) -> None:
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    scenarios = response.json()["scenarios"]
    assert [item["scenario_id"] for item in scenarios] == list("abcdef")
    assert all(item["title"] for item in scenarios)


def test_single_simulation(client: TestClient) -> None:
    response = client.post(
        "/api/simulate",
        json={"L_w_m": 0.0, "h_w_m": 12.0, "profile_points": 101},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["scenario_id"] == "e"
    assert body["toe_location_x_t_m"] == pytest.approx(106.16479288326705)
    assert body["toe_location_uncorrected_m"] == pytest.approx(178.94230343961368)
    assert len(body["profiles"]) > 101
    assert body["profiles"][0]["interface_elevation_zeta_m"] == pytest.approx(30.0)
    assert any("not a no-wall baseline" in warning for warning in body["warnings"])
    assert body["metadata"]["correction_mode"] == "pool_carrera_flux"


def test_no_wall_simulation(client: TestClient) -> None:
    response = client.post("/api/simulate", json={"mode": "no_wall"})
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_title"] == "No cutoff wall (baseline)"
    assert body["toe_location_x_t_m"] == pytest.approx(191.71959564551693)


@pytest.mark.parametrize(
    "payload",
    [
        {"h_w_m": 12.0},
        {"L_w_m": 0.0},
        {"L_w_m": -1.0, "h_w_m": 12.0},
        {"L_w_m": 0.0, "h_w_m": 30.0},
        {"L_w_m": 0.0, "h_w_m": 12.0, "unexpected": 1},
        {"L_w_m": 0.0, "h_w_m": 12.0, "profile_points": 1},
    ],
)
def test_invalid_single_simulation_requests(
    client: TestClient, payload: dict
) -> None:
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] in {
        "VALIDATION_ERROR",
        "SIMULATION_INPUT_ERROR",
    }


def test_batch_default_16_cases(client: TestClient) -> None:
    response = client.post("/api/simulate/batch", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["total"] == 16
    assert body["successful"] == 16
    assert body["failed"] == 0
    assert {case["scenario_id"] for case in body["cases"]} == {"c", "e"}
    assert len({(case["L_w_m"], case["h_w_m"]) for case in body["cases"]}) == 16


def test_empty_batch_is_rejected(client: TestClient) -> None:
    response = client.post("/api/simulate/batch", json={"configurations": []})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EMPTY_BATCH"


def test_validation_endpoint(client: TestClient) -> None:
    response = client.post("/api/validate", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "passed"
    assert body["total_checks"] == 14

    uncorrected = client.post(
        "/api/validate", json={"correction_mode": "none"}
    )
    assert uncorrected.status_code == 200
    assert uncorrected.json()["validation_status"] == "not_applicable"


def test_dataset_generation_and_results(
    client: TestClient, generated_dataset: dict
) -> None:
    assert generated_dataset["total_cases"] == 16
    assert generated_dataset["successful"] == 16
    assert generated_dataset["validation_status"] == "passed"
    assert generated_dataset["manifest"]["case_count"] == 16
    assert generated_dataset["manifest"]["sha256"]["results_csv"]

    results = client.get("/api/results")
    assert results.status_code == 200
    body = results.json()
    assert body["generated"] is True
    assert len(body["cases"]) == 16
    assert body["manifest"]["validation_status"] == "passed"


def test_dataset_download(
    client: TestClient, generated_dataset: dict
) -> None:
    response = client.get("/api/dataset/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            "simulation_cases.csv",
            "simulation_results.csv",
            "profiles.csv",
            "manifest.json",
        }
        assert archive.testzip() is None


def test_dataset_download_missing_returns_404(
    client: TestClient, monkeypatch, tmp_path
) -> None:
    import app.services.dataset_service as dataset_service

    monkeypatch.setattr(dataset_service, "CASES_CSV", tmp_path / "missing_cases.csv")
    monkeypatch.setattr(dataset_service, "RESULTS_CSV", tmp_path / "missing_results.csv")
    monkeypatch.setattr(dataset_service, "PROFILES_CSV", tmp_path / "missing_profiles.csv")
    monkeypatch.setattr(dataset_service, "MANIFEST_JSON", tmp_path / "missing_manifest.json")
    response = client.get("/api/dataset/download")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "DATASET_NOT_FOUND"
