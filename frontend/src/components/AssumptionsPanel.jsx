import { formatCompact } from "../utils/format.js";

export default function AssumptionsPanel({ parameters, scenarios = [] }) {
  const assumptions = parameters?.assumptions || [
    "Steady state",
    "Confined aquifer",
    "Sharp interface",
    "Constant inland freshwater flux",
    "Dupuit–Forchheimer approximation",
  ];
  const paper = parameters?.paper;

  return (
    <section className="card assumptions-card" aria-labelledby="assumptions-title">
      <div className="card-heading">
        <div>
          <p className="eyebrow">Scope and provenance</p>
          <h2 id="assumptions-title">Assumptions and limitations</h2>
        </div>
      </div>

      <ul className="assumption-list">
        {assumptions.map((assumption) => (
          <li key={assumption}>{assumption}</li>
        ))}
      </ul>

      <div className="provenance">
        <h3>Generated dataset notice</h3>
        <p>
          All cases in this application are physics-based analytical simulations.
          They are not field observations, and no SEAWAT or other numerical
          validation was performed in this project.
        </p>
      </div>

      <div className="citation">
        <h3>Primary source</h3>
        <p>
          {paper?.title || "A novel analytical solution for quantifying seawater intrusion in coastal aquifers embedded with a cutoff wall"}
        </p>
        <p className="muted">
          {paper?.journal || "Advances in Water Resources 212 (2026) 105301"}
        </p>
        <a
          href={`https://doi.org/${paper?.doi || "10.1016/j.advwatres.2026.105301"}`}
          target="_blank"
          rel="noreferrer"
        >
          doi:{paper?.doi || "10.1016/j.advwatres.2026.105301"}
        </a>
      </div>

      {scenarios.length > 0 && (
        <details className="scenario-definitions">
          <summary>Scenario definitions from Eq. (23)</summary>
          <div className="scenario-definition-list">
            {scenarios.map((scenario) => (
              <div key={scenario.scenario_id} className="scenario-definition">
                <span className="scenario-tag">{scenario.scenario_id.toUpperCase()}</span>
                <div>
                  <strong>{scenario.title}</strong>
                  <p>{scenario.description}</p>
                  <code>{scenario.condition_text}</code>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      <div className="assumption-footnote">
        Reference toe values are text-reported values used with a 0.5 m tolerance.
        The paper text calls panels *2 an 18 m wall, while the Fig. 4 caption
        defines index 2 as h<sub>w</sub> = 12 m. The 12 m solution reproduces the
        reported values. Dimensionless no-wall toe x<sub>t</sub><sup>a</sup> ={" "}
        {formatCompact(parameters?.derived?.x_t_no_wall_m)} m.
      </div>
    </section>
  );
}
