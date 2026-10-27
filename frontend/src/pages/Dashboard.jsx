import { useEffect, useState } from "react";
import {
  downloadDataset,
  generateDataset,
  getHealth,
  getParameters,
  getResults,
  getScenarios,
  runValidation,
  simulate,
  simulateBatch,
} from "../api/client.js";
import AssumptionsPanel from "../components/AssumptionsPanel.jsx";
import ParameterPanel from "../components/ParameterPanel.jsx";
import ProfileChart from "../components/ProfileChart.jsx";
import ResultsTable from "../components/ResultsTable.jsx";
import ScenarioSummary from "../components/ScenarioSummary.jsx";
import ToeResultCard from "../components/ToeResultCard.jsx";
import ValidationPanel from "../components/ValidationPanel.jsx";
import { formatNumber, statusLabel } from "../utils/format.js";

const INITIAL_FORM = {
  L_w_m: 0,
  h_w_m: 12,
  correctionMode: "pool_carrera_flux",
  mode: "wall",
};

function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [parameters, setParameters] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [offline, setOffline] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);

  const [result, setResult] = useState(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState(null);

  const [batch, setBatch] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchError, setBatchError] = useState(null);

  const [validation, setValidation] = useState(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState(null);

  const [datasetInfo, setDatasetInfo] = useState(null);
  const [datasetLoading, setDatasetLoading] = useState(false);
  const [datasetError, setDatasetError] = useState(null);
  const [downloadLoading, setDownloadLoading] = useState(false);

  async function loadDashboard() {
    setOffline(null);
    try {
      const [healthData, parameterData, scenarioData, resultsData] =
        await Promise.all([
          getHealth(),
          getParameters(),
          getScenarios(),
          getResults(),
        ]);
      setHealth(healthData);
      setParameters(parameterData);
      setScenarios(scenarioData.scenarios || []);
      setDatasetInfo(resultsData.manifest || null);
      setOffline(null);
    } catch (error) {
      setOffline(errorMessage(error));
      return;
    }

    try {
      setValidationLoading(true);
      const validationData = await runValidation(form.correctionMode);
      setValidation(validationData);
      setValidationError(null);
    } catch (error) {
      setValidationError(errorMessage(error));
    } finally {
      setValidationLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
    // The initial dashboard load is intentionally performed once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRun(mode) {
    setRunLoading(true);
    setRunError(null);
    try {
      const payload =
        mode === "no_wall"
          ? {
              mode: "no_wall",
              correction_mode: form.correctionMode,
              include_profiles: true,
              profile_points: 401,
            }
          : {
              mode: "wall",
              L_w_m: form.L_w_m,
              h_w_m: form.h_w_m,
              correction_mode: form.correctionMode,
              include_profiles: true,
              profile_points: 401,
            };
      const data = await simulate(payload);
      setResult(data);
    } catch (error) {
      setRunError(errorMessage(error));
    } finally {
      setRunLoading(false);
    }
  }

  async function handleBatch() {
    setBatchLoading(true);
    setBatchError(null);
    try {
      const data = await simulateBatch({
        correction_mode: form.correctionMode,
        include_profiles: false,
      });
      setBatch(data);
    } catch (error) {
      setBatchError(errorMessage(error));
    } finally {
      setBatchLoading(false);
    }
  }

  async function handleValidate() {
    setValidationLoading(true);
    setValidationError(null);
    try {
      const data = await runValidation(form.correctionMode);
      setValidation(data);
      const [healthData, resultsData] = await Promise.all([
        getHealth(),
        getResults(),
      ]);
      setHealth(healthData);
      setDatasetInfo(resultsData.manifest || null);
    } catch (error) {
      setValidationError(errorMessage(error));
    } finally {
      setValidationLoading(false);
    }
  }

  async function handleGenerateDataset() {
    setDatasetLoading(true);
    setDatasetError(null);
    try {
      const data = await generateDataset(form.correctionMode);
      setDatasetInfo(data.manifest);
      const [validationData, resultsData, healthData] = await Promise.all([
        runValidation(form.correctionMode),
        getResults(),
        getHealth(),
      ]);
      setValidation(validationData);
      setDatasetInfo(resultsData.manifest || data.manifest);
      setHealth(healthData);
      setValidationError(null);
    } catch (error) {
      setDatasetError(errorMessage(error));
    } finally {
      setDatasetLoading(false);
    }
  }

  async function handleDownload() {
    setDownloadLoading(true);
    setDatasetError(null);
    try {
      const blob = await downloadDataset();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "seawater_intrusion_dataset.zip";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setDatasetError(errorMessage(error));
    } finally {
      setDownloadLoading(false);
    }
  }

  const online = Boolean(health?.status === "ok") && !offline;
  const currentValidation =
    validation?.metadata?.correction_mode === form.correctionMode
      ? validation
      : null;
  const validated = currentValidation?.validation_status === "passed";
  const validationBadge = validated
    ? "Validated"
    : currentValidation?.validation_status === "failed"
      ? "Validation failed"
      : currentValidation?.validation_status === "not_applicable"
        ? "Validation not applicable"
        : "Validation pending";
  const isBaseline = Boolean(result?.metadata?.baseline);
  const wallStart = isBaseline ? undefined : result?.parameters?.L_w_m;
  const wallEnd =
    isBaseline || result?.parameters?.L_w_m === undefined
      ? undefined
      : result.parameters.L_w_m + result.parameters.wall_thickness_m;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-copy">
          <p className="eyebrow">Coastal groundwater · confined aquifer</p>
          <h1>Seawater Intrusion Analytical Simulator</h1>
          <p className="header-subtitle">
            Steady-state sharp-interface analysis of a cutoff wall under a
            constant inland freshwater flux, based on Sun et al. (2026).
          </p>
        </div>
        <div className="header-badges">
          <span className="badge analytic">Analytical simulation</span>
          <span className={`status-pill ${online ? "success" : "failed"}`}>
            {online ? "Backend online" : "Backend offline"}
          </span>
          <span
            className={`status-pill ${
              validated
                ? "success"
                : currentValidation?.validation_status === "failed"
                  ? "failed"
                  : "not-run"
            }`}
          >
            {validationBadge}
          </span>
        </div>
      </header>

      {offline && (
        <div className="offline-banner" role="alert">
          <div>
            <strong>Backend connection required</strong>
            <p>{offline}</p>
          </div>
          <button className="button secondary" onClick={loadDashboard}>
            Retry connection
          </button>
        </div>
      )}

      {runError && (
        <div className="error-banner" role="alert">
          <strong>Simulation failed</strong>
          <span>{runError}</span>
        </div>
      )}

      <main>
        <div className="top-grid">
          <ParameterPanel
            parameters={parameters}
            form={form}
            setForm={setForm}
            onRun={() => handleRun("wall")}
            onNoWall={() => handleRun("no_wall")}
            loading={runLoading}
            disabled={!online}
          />
          <div className="result-stack">
            <ToeResultCard result={result} />
            <ScenarioSummary result={result} />
          </div>
        </div>

        <div className="chart-grid">
          <ProfileChart
            title="Hydraulic head"
            subtitle="φ(x) profile"
            data={result?.profiles}
            dataKey="hydraulic_head_phi_m"
            seriesName="Hydraulic head φ"
            yAxisLabel="Hydraulic head φ (m)"
            wallStart={wallStart}
            wallEnd={wallEnd}
            toe={result?.toe_location_x_t_m}
            emptyMessage="Run a wall simulation or the no-wall baseline to display the head profile."
          />
          <ProfileChart
            title="Interface elevation"
            subtitle="ζ(x) profile"
            data={result?.profiles}
            dataKey="interface_elevation_zeta_m"
            seriesName="Interface elevation ζ"
            yAxisLabel="Interface elevation ζ (m)"
            wallStart={wallStart}
            wallEnd={wallEnd}
            toe={result?.toe_location_x_t_m}
            emptyMessage="The interface profile appears after a successful simulation. Undefined regions are not drawn."
          />
        </div>

        <section className="card batch-card" aria-labelledby="batch-title">
          <div className="card-heading batch-heading">
            <div>
              <p className="eyebrow">Generated experiments</p>
              <h2 id="batch-title">16-case batch and dataset</h2>
            </div>
            <div className="button-row">
              <button className="button primary" onClick={handleBatch} disabled={batchLoading || !online}>
                {batchLoading ? "Running batch…" : "Run 16 cases"}
              </button>
              <button
                className="button secondary"
                onClick={handleGenerateDataset}
                disabled={datasetLoading || !online}
              >
                {datasetLoading ? "Generating…" : "Generate dataset"}
              </button>
              <button
                className="button ghost"
                onClick={handleDownload}
                disabled={downloadLoading || !datasetInfo || !online}
              >
                {downloadLoading ? "Preparing ZIP…" : "Download ZIP"}
              </button>
            </div>
          </div>

          {batchError && <div className="error-box">{batchError}</div>}
          {datasetError && <div className="error-box">{datasetError}</div>}

          <div className="batch-summary-grid">
            <div className="batch-stat">
              <span>Batch status</span>
              <strong>{batch ? statusLabel(batch.status) : "Not run"}</strong>
            </div>
            <div className="batch-stat">
              <span>Successful</span>
              <strong>{batch ? `${batch.successful} / ${batch.total}` : "—"}</strong>
            </div>
            <div className="batch-stat">
              <span>Failed</span>
              <strong>{batch ? batch.failed : "—"}</strong>
            </div>
            <div className="batch-stat">
              <span>Latest dataset</span>
              <strong>
                {datasetInfo
                  ? `${datasetInfo.successful_cases ?? "—"} cases`
                  : "Not generated"}
              </strong>
            </div>
            <div className="batch-stat">
              <span>Dataset validation</span>
              <strong>{statusLabel(datasetInfo?.validation_status || "not_run")}</strong>
            </div>
            <div className="batch-stat">
              <span>Generated at</span>
              <strong className="small-strong">
                {datasetInfo?.generated_at
                  ? new Date(datasetInfo.generated_at).toLocaleString()
                  : "—"}
              </strong>
            </div>
          </div>

          <ResultsTable cases={batch?.cases || []} />
        </section>

        <div className="bottom-grid">
          <ValidationPanel
            validation={currentValidation}
            onValidate={handleValidate}
            loading={validationLoading}
            error={validationError}
          />
          <AssumptionsPanel parameters={parameters} scenarios={scenarios} />
        </div>
      </main>

      <footer className="app-footer">
        <span>
          Model version {health?.model_version || "sun2026-confined-cutoff-v1"} ·
          app {health?.app_version || "1.0.0"}
        </span>
        <span>
          x<sub>t</sub> = {result ? `${formatNumber(result.toe_location_x_t_m, 2)} m` : "—"} ·
          q<sub>f</sub> boundary · generated results are not field data
        </span>
      </footer>
    </div>
  );
}
