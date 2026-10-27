import { statusLabel } from "../utils/format.js";

export default function ScenarioSummary({ result }) {
  if (!result) {
    return (
      <section className="card scenario-card empty-card" aria-labelledby="scenario-title">
        <div>
          <p className="eyebrow">Scenario detection</p>
          <h2 id="scenario-title">Run a configuration</h2>
          <p className="muted">
            The backend will classify the wall/interface geometry using the
            paper’s Eq. (23) conditions and show the matching scenario here.
          </p>
        </div>
      </section>
    );
  }

  const hasWarnings = result.warnings?.length > 0;

  return (
    <section className="card scenario-card" aria-labelledby="scenario-title">
      <div className="scenario-banner">
        <div className="scenario-letter">{result.scenario_id}</div>
        <div>
          <p className="eyebrow">Detected scenario</p>
          <h2 id="scenario-title">{result.scenario_title}</h2>
        </div>
        <span className="status-pill success">{statusLabel(result.status)}</span>
      </div>

      <p className="scenario-description">{result.scenario_description}</p>

      <dl className="detail-list">
        <div>
          <dt>Classification rule</dt>
          <dd>{result.scenario_condition}</dd>
        </div>
        <div>
          <dt>Correction mode</dt>
          <dd>{result.parameters?.correction_mode === "none" ? "Uncorrected" : "Pool–Carrera Eq. (43)"}</dd>
        </div>
        <div>
          <dt>Wall interval</dt>
          <dd>
            {result.parameters?.L_w_m} m to{" "}
            {(result.parameters?.L_w_m ?? 0) + (result.parameters?.wall_thickness_m ?? 0)} m
          </dd>
        </div>
      </dl>

      {hasWarnings && (
        <div className="warning-box">
          <strong>Model warnings</strong>
          <ul>
            {result.warnings.map((warning, index) => (
              <li key={`${warning}-${index}`}>{warning}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
