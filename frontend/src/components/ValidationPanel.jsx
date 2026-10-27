import { formatCompact, formatDifference, statusLabel } from "../utils/format.js";

export default function ValidationPanel({ validation, onValidate, loading, error }) {
  const passed = validation?.validation_status === "passed";

  return (
    <section className="card validation-card" aria-labelledby="validation-title">
      <div className="card-heading">
        <div>
          <p className="eyebrow">Automated checks</p>
          <h2 id="validation-title">Model validation</h2>
        </div>
        <span className={`status-pill ${passed ? "success" : validation?.validation_status || "not-run"}`}>
          {passed ? "Validated" : statusLabel(validation?.validation_status || "not_run")}
        </span>
      </div>

      <p className="muted">
        Mathematical invariants are checked separately from comparisons with
        values reported in Sun et al. (2026). Generated data is never labelled
        validated before these checks pass.
      </p>

      {validation && (
        <div className="validation-summary">
          <div>
            <span>Math</span>
            <strong>{statusLabel(validation.math_status)}</strong>
          </div>
          <div>
            <span>Paper</span>
            <strong>{statusLabel(validation.paper_status)}</strong>
          </div>
          <div>
            <span>Passed</span>
            <strong>{validation.passed_checks}</strong>
          </div>
          <div>
            <span>Failed</span>
            <strong>{validation.failed_checks}</strong>
          </div>
          <div>
            <span>Not applicable</span>
            <strong>{validation.not_applicable_checks}</strong>
          </div>
        </div>
      )}

      {error && <div className="error-box">{error}</div>}

      {!validation ? (
        <div className="validation-empty">
          <p>No validation response loaded.</p>
          <button className="button secondary" onClick={onValidate} disabled={loading}>
            {loading ? "Running checks…" : "Run validation"}
          </button>
        </div>
      ) : (
        <>
          <div className="table-scroll validation-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Check</th>
                  <th>Layer</th>
                  <th>Status</th>
                  <th>Reference</th>
                  <th>Computed</th>
                  <th>Abs. diff.</th>
                  <th>Tolerance</th>
                </tr>
              </thead>
              <tbody>
                {validation.checks.map((check) => (
                  <tr key={check.check_id} title={check.notes || check.source}>
                    <td>
                      <strong>{check.name}</strong>
                      <span className="source-line">{check.source}</span>
                    </td>
                    <td>{check.layer}</td>
                    <td>
                      <span className={`status-pill ${check.status}`}>
                        {statusLabel(check.status)}
                      </span>
                    </td>
                    <td>{typeof check.reference === "number" ? formatCompact(check.reference) : check.reference || "—"}</td>
                    <td>{typeof check.computed === "number" ? formatCompact(check.computed) : check.computed || "—"}</td>
                    <td>{formatDifference(check.absolute_difference)}</td>
                    <td>{formatCompact(check.tolerance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="validation-footer">
            <span>
              Checked {validation.total_checks} items ·{" "}
              {validation.metadata?.correction_mode === "none"
                ? "Uncorrected mode"
                : "Pool–Carrera correction"}
            </span>
            <button className="button ghost compact" onClick={onValidate} disabled={loading}>
              {loading ? "Running…" : "Re-run checks"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
