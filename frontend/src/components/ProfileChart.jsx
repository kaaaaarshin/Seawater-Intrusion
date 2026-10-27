import {
  CartesianGrid,
  Label,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumber } from "../utils/format.js";

export default function ProfileChart({
  title,
  subtitle,
  data,
  dataKey,
  seriesName,
  yAxisLabel,
  wallStart,
  wallEnd,
  toe,
  emptyMessage,
}) {
  const chartData =
    dataKey === "interface_elevation_zeta_m"
      ? (data || []).filter(
          (point) =>
            point.interface_defined &&
            point.interface_elevation_zeta_m !== null &&
            point.interface_elevation_zeta_m !== undefined,
        )
      : data || [];

  return (
    <section className="card chart-card" aria-labelledby={`${dataKey}-title`}>
      <div className="card-heading">
        <div>
          <p className="eyebrow">{subtitle}</p>
          <h2 id={`${dataKey}-title`}>{title}</h2>
        </div>
        <span className="unit-chip">m</span>
      </div>

      {chartData.length === 0 ? (
        <div className="chart-empty">{emptyMessage}</div>
      ) : (
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={330}>
            <LineChart data={chartData} margin={{ top: 22, right: 22, bottom: 30, left: 14 }}>
              <CartesianGrid stroke="#dce7e4" strokeDasharray="3 4" vertical={false} />
              <XAxis
                dataKey="x_m"
                type="number"
                domain={[0, "dataMax"]}
                tickFormatter={(value) => formatNumber(value, 0)}
                tick={{ fill: "#526a68", fontSize: 12 }}
                axisLine={{ stroke: "#9db7b1" }}
                tickLine={false}
              >
                <Label
                  value="Distance from coastline x (m)"
                  position="insideBottom"
                  offset={-18}
                  fill="#526a68"
                  fontSize={12}
                />
              </XAxis>
              <YAxis
                domain={["auto", "auto"]}
                tickFormatter={(value) => formatNumber(value, 0)}
                tick={{ fill: "#526a68", fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                width={68}
              >
                <Label
                  value={yAxisLabel}
                  angle={-90}
                  position="insideLeft"
                  offset={6}
                  fill="#526a68"
                  fontSize={12}
                />
              </YAxis>
              <Tooltip
                contentStyle={{
                  borderRadius: 10,
                  border: "1px solid #c8dcd7",
                  boxShadow: "0 8px 24px rgba(16, 61, 58, 0.12)",
                }}
                labelFormatter={(value) => `x = ${formatNumber(value, 2)} m`}
                formatter={(value) => [`${formatNumber(value, 3)} m`, seriesName]}
              />
              <Legend verticalAlign="top" height={28} iconType="plainline" />
              {Number.isFinite(wallStart) && (
                <ReferenceLine
                  x={wallStart}
                  stroke="#9b6b2f"
                  strokeDasharray="5 4"
                  label={{ value: "L_w", position: "top", fill: "#7b5322", fontSize: 11 }}
                />
              )}
              {Number.isFinite(wallEnd) && (
                <ReferenceLine
                  x={wallEnd}
                  stroke="#9b6b2f"
                  strokeDasharray="2 4"
                  label={{ value: "L_w + w", position: "top", fill: "#7b5322", fontSize: 11 }}
                />
              )}
              {Number.isFinite(toe) && (
                <ReferenceLine
                  x={toe}
                  stroke="#c04545"
                  strokeWidth={1.5}
                  label={{ value: "x_t", position: "insideTopRight", fill: "#a33131", fontSize: 11 }}
                />
              )}
              <Line
                type="monotone"
                dataKey={dataKey}
                name={seriesName}
                stroke="#0e6f73"
                strokeWidth={2.4}
                dot={false}
                activeDot={{ r: 4 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="chart-note">
        {dataKey === "interface_elevation_zeta_m"
          ? "The interface is plotted only where the analytical solution defines it; no curve is drawn inland of the toe."
          : "Hydraulic head is shown across the full domain. Inland of the toe, the head follows the constant-flux freshwater zone."}
      </p>
    </section>
  );
}
