import { formatCompact, formatNumber } from "../utils/format.js";

export default function ToeResultCard({ result }) {
  if (!result) {
    return (
      <section className="card" aria-labelledby="metrics-title">
        <div className="card-heading">
          <div>
            <p className="eyebrow">Results</p>
            <h2 id="metrics-title">Interface metrics</h2>
          </div>
        </div>
        <div className="empty-metrics">
          <span className="empty-value">—</span>
          <p>Toe location and head diagnostics appear after a successful run.</p>
        </div>
      </section>
    );
  }

  const metrics = [
    {
      label: "Interface toe",
      symbol: "x_t",
      value: formatNumber(result.toe_location_x_t_m, 2),
      unit: "m",
      tone: "primary",
    },
    {
      label: "Uncorrected toe",
      symbol: "x_t (α = 40)",
      value: formatNumber(result.toe_location_uncorrected_m, 2),
      unit: "m",
    },
    {
      label: "Wall intersection",
      symbol: "x_h",
      value: formatNumber(result.xh_m, 2),
      unit: "m",
    },
    {
      label: "No-wall reference",
      symbol: "x_t^a",
      value: formatNumber(result.x_t_no_wall_m, 2),
      unit: "m",
    },
    {
      label: "Head at x = L",
      symbol: "φ(L)",
      value: formatNumber(result.head_at_inland_boundary_m, 2),
      unit: "m",
    },
    {
      label: "Toe reduction",
      symbol: "Δx_t",
      value: formatNumber(result.x_t_no_wall_m - result.toe_location_x_t_m, 2),
      unit: "m",
    },
  ];

  return (
    <section className="card" aria-labelledby="metrics-title">
      <div className="card-heading">
        <div>
          <p className="eyebrow">Results</p>
          <h2 id="metrics-title">Interface metrics</h2>
        </div>
        <span className="unit-chip">Dimensional</span>
      </div>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <div
            className={`metric ${metric.tone === "primary" ? "metric-primary" : ""}`}
            key={metric.label}
          >
            <span className="metric-label">{metric.label}</span>
            <span className="metric-symbol">{metric.symbol}</span>
            <span className="metric-value">
              {metric.value} <small>{metric.unit}</small>
            </span>
          </div>
        ))}
      </div>
      <p className="metric-footnote">
        Corrected toe uses Eq. (43); the uncorrected sharp-interface comparison is
        always reported separately. Dimensionless toe x<sub>t</sub> ={" "}
        {formatCompact(result.toe_dimensionless)}.
      </p>
    </section>
  );
}
