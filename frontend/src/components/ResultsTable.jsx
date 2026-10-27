import { useMemo, useState } from "react";
import { formatNumber, statusLabel } from "../utils/format.js";

export default function ResultsTable({ cases }) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [scenarioFilter, setScenarioFilter] = useState("all");
  const [sortKey, setSortKey] = useState("case_id");
  const [descending, setDescending] = useState(false);

  const scenarios = useMemo(
    () => [...new Set(cases.map((item) => item.scenario_id).filter(Boolean))].sort(),
    [cases],
  );

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();
    const rows = cases.filter((item) => {
      const matchesSearch =
        !search ||
        item.case_id?.toLowerCase().includes(search) ||
        String(item.L_w_m).includes(search) ||
        String(item.h_w_m).includes(search);
      const matchesStatus =
        statusFilter === "all" || item.status === statusFilter;
      const matchesScenario =
        scenarioFilter === "all" || item.scenario_id === scenarioFilter;
      return matchesSearch && matchesStatus && matchesScenario;
    });

    return rows.sort((left, right) => {
      const a = left[sortKey];
      const b = right[sortKey];
      if (a === b) return 0;
      if (a === null || a === undefined) return 1;
      if (b === null || b === undefined) return -1;
      const direction = descending ? -1 : 1;
      return a > b ? direction : -direction;
    });
  }, [cases, query, statusFilter, scenarioFilter, sortKey, descending]);

  if (cases.length === 0) {
    return (
      <div className="table-empty">
        No batch results yet. Run the 16 planned configurations to populate this
        table.
      </div>
    );
  }

  return (
    <>
      <div className="table-controls">
        <label className="search-field">
          <span className="sr-only">Search cases</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search case, L_w, h_w"
          />
        </label>
        <label className="compact-field">
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <label className="compact-field">
          <span>Scenario</span>
          <select
            value={scenarioFilter}
            onChange={(event) => setScenarioFilter(event.target.value)}
          >
            <option value="all">All</option>
            {scenarios.map((scenario) => (
              <option value={scenario} key={scenario}>
                {scenario.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
        <label className="compact-field">
          <span>Sort</span>
          <select value={sortKey} onChange={(event) => setSortKey(event.target.value)}>
            <option value="case_id">Case</option>
            <option value="L_w_m">L_w</option>
            <option value="h_w_m">h_w</option>
            <option value="toe_location_x_t_m">Toe</option>
            <option value="scenario_id">Scenario</option>
          </select>
        </label>
        <button
          className="button ghost compact"
          onClick={() => setDescending((current) => !current)}
          type="button"
        >
          {descending ? "Descending" : "Ascending"}
        </button>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Case</th>
              <th>L_w (m)</th>
              <th>h_w (m)</th>
              <th>Scenario</th>
              <th>x_t (m)</th>
              <th>x_t uncorrected (m)</th>
              <th>Status</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.case_id}>
                <td className="mono">{item.case_id}</td>
                <td>{formatNumber(item.L_w_m, 0)}</td>
                <td>{formatNumber(item.h_w_m, 0)}</td>
                <td>
                  <span className="scenario-tag">
                    {item.scenario_id?.toUpperCase() || "—"}
                  </span>
                </td>
                <td>{formatNumber(item.toe_location_x_t_m, 2)}</td>
                <td>{formatNumber(item.toe_location_uncorrected_m, 2)}</td>
                <td>
                  <span className={`status-pill ${item.status}`}>
                    {statusLabel(item.status)}
                  </span>
                </td>
                <td className="notes-cell">
                  {item.error?.message ||
                    (item.warnings?.length ? item.warnings.join(" ") : "—")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="table-summary">
        Showing {filtered.length} of {cases.length} cases. The table is populated
        by the backend batch response, not by client-side calculations.
      </p>
    </>
  );
}
