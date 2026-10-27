import { formatNumber } from "../utils/format.js";

export default function ParameterPanel({
  parameters,
  form,
  setForm,
  onRun,
  onNoWall,
  loading,
  disabled = false,
}) {
  const locations = parameters?.allowed_wall_locations_m || [0, 38, 77, 115];
  const heights = parameters?.allowed_wall_opening_heights_m || [6, 12, 18, 24];
  const fixed = (parameters?.parameters || []).filter((item) =>
    ["H_m", "H_s_m", "K_a_m_per_day", "K_w_m_per_day", "wall_thickness_m", "q_f_m2_per_day"].includes(
      item.key,
    ),
  );

  return (
    <section className="card parameter-panel" aria-labelledby="parameter-title">
      <div className="card-heading">
        <div>
          <p className="eyebrow">Configuration</p>
          <h2 id="parameter-title">Cutoff wall and aquifer</h2>
        </div>
        <span className="unit-chip">SI units</span>
      </div>

      <div className="field-grid">
        <label className="field">
          <span>Wall location L<sub>w</sub></span>
          <select
            value={form.L_w_m}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                L_w_m: Number(event.target.value),
              }))
            }
            disabled={loading || disabled || form.mode === "no_wall"}
          >
            {locations.map((value) => (
              <option key={value} value={value}>
                {value} m
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Opening height h<sub>w</sub></span>
          <select
            value={form.h_w_m}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                h_w_m: Number(event.target.value),
              }))
            }
            disabled={loading || disabled || form.mode === "no_wall"}
          >
            {heights.map((value) => (
              <option key={value} value={value}>
                {value} m
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="field">
        <span>Interface treatment</span>
        <select
          value={form.correctionMode}
          onChange={(event) =>
            setForm((current) => ({
              ...current,
              correctionMode: event.target.value,
            }))
          }
          disabled={loading || disabled}
        >
          <option value="pool_carrera_flux">Pool–Carrera correction (Eq. 43)</option>
          <option value="none">Uncorrected sharp interface (α = 40)</option>
        </select>
      </label>

      <div className="boundary-note">
        <strong>Inland boundary</strong>
        <span>Constant freshwater flux q<sub>f</sub> at x = L</span>
        <span className="mono">
          q<sub>f</sub> = {formatNumber(parameters?.parameters?.find((p) => p.key === "q_f_m2_per_day")?.value, 3)} m²/day
        </span>
      </div>

      <div className="fixed-parameters">
        {fixed.map((item) => (
          <div className="fixed-parameter" key={item.key}>
            <span className="fixed-symbol">{item.symbol}</span>
            <span className="fixed-value">{formatNumber(item.value, item.value < 1 ? 4 : 2)}</span>
            <span className="fixed-unit">{item.unit}</span>
          </div>
        ))}
      </div>

      <div className="derived-row">
        <span>α = {formatNumber(parameters?.derived?.alpha_base, 0)}</span>
        <span>α′ = {formatNumber(parameters?.derived?.alpha_effective, 2)}</span>
        <span>κ = {formatNumber(parameters?.derived?.kappa, 4)}</span>
        <span>x<sub>t</sub><sup>a</sup> = {formatNumber(parameters?.derived?.x_t_no_wall_m, 1)} m</span>
      </div>

      <div className="button-row">
        <button className="button primary" onClick={onRun} disabled={loading || disabled}>
          {loading ? "Running…" : "Run wall simulation"}
        </button>
        <button className="button secondary" onClick={onNoWall} disabled={loading || disabled}>
          {loading ? "Running…" : "No-wall baseline"}
        </button>
      </div>
      <p className="fine-print">
        L<sub>w</sub> = 0 is a wall at the coastline, not a no-wall case. The explicit
        baseline is a separate analytical run.
      </p>
    </section>
  );
}
