"use client";

import {
 Area,
 CartesianGrid,
 ComposedChart,
 Legend,
 Line,
 ResponsiveContainer,
 Tooltip,
 XAxis,
 YAxis,
} from "recharts";

import type { Forecast } from "@/lib/api";
import { useThemeColors } from "@/lib/use-theme-colors";
import { shortDate } from "@/lib/utils";

interface Row {
 date: string;
 actual?: number;
 driver?: number;
 predicted?: number;
 band?: [number, number];
}

function buildRows(forecast: Forecast): Row[] {
 const byDate = new Map<string, Row>();

 for (const point of forecast.history) {
 byDate.set(point.date, { date: point.date, actual: point.value });
 }
 for (const point of forecast.driver_history) {
 const row = byDate.get(point.date) ?? { date: point.date };
 row.driver = point.value;
 byDate.set(point.date, row);
 }

 const rows = [...byDate.values()].sort((a, b) =>
 a.date.localeCompare(b.date),
 );

 // Прогнозната линия тръгва от последното реално наблюдение, за да няма
 // визуален скок между историята и прогнозата.
 const lastActual = rows.filter((r) => r.actual !== undefined).at(-1);
 if (lastActual) {
 lastActual.predicted = lastActual.actual;
 lastActual.band = [lastActual.actual!, lastActual.actual!];
 }

 for (const point of forecast.points) {
 rows.push({
 date: point.target_date,
 predicted: point.predicted_value,
 band: [point.ci_lower, point.ci_upper],
 });
 }

 return rows;
}

export function ForecastChart({ forecast }: { forecast: Forecast }) {
 const rows = buildRows(forecast);
  const c = useThemeColors();

 const latest = forecast.history.at(-1);
 const last = forecast.points.at(-1);

 return (
 <figure className="m-0">
 <figcaption className="sr-only">
 Графика на средната лихва по нови жилищни кредити в България спрямо
 германската 10-годишна доходност. Последно отчетено{" "}
 {latest ? `${latest.value.toFixed(2)}% на ${latest.date}` : "няма данни"}.
 Прогнозата за {last?.horizon_days ?? 180} дни е{" "}
 {last ? `${last.predicted_value.toFixed(2)}%` : "недостъпна"}.
 </figcaption>
 <div className="h-[340px] w-full">
 <ResponsiveContainer width="100%" height="100%">
 <ComposedChart
 data={rows}
 margin={{ top: 8, right: 8, bottom: 4, left: -18 }}
 >
 <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
 <XAxis
 dataKey="date"
 tickFormatter={shortDate}
 tick={{ fontSize: 11, fill: c.muted }}
 minTickGap={28}
 />
 <YAxis
 tick={{ fontSize: 11, fill: c.muted }}
 tickFormatter={(v: number) => `${v.toFixed(1)}%`}
 domain={["auto", "auto"]}
 />
 <Tooltip
 labelFormatter={(label) =>
 typeof label === "string" ? shortDate(label) : ""
 }
 formatter={(value, name) => {
 if (Array.isArray(value)) {
 return [
 `${Number(value[0]).toFixed(2)}% – ${Number(value[1]).toFixed(2)}%`,
 String(name),
 ];
 }
 return [`${Number(value).toFixed(2)}%`, String(name)];
 }}
 contentStyle={{
 borderRadius: 12,
 border: "1px solid hsl(var(--border))",
 background: "hsl(var(--card))",
 fontSize: 12,
 }}
 />
 <Legend wrapperStyle={{ fontSize: 12 }} />
 <Area
 dataKey="band"
 name="Диапазон на прогнозата (95%)"
 stroke="none"
 fill={c.primary}
 fillOpacity={0.16}
 connectNulls
 isAnimationActive={false}
 />
 <Line
 dataKey="driver"
 name="Германска 10-г. облигация"
 stroke={c.muted}
 strokeWidth={1.5}
 dot={false}
 connectNulls
 isAnimationActive={false}
 />
 <Line
 dataKey="actual"
 name="Лихва в България (реална)"
 stroke={c.primary}
 strokeWidth={2.5}
 dot={false}
 isAnimationActive={false}
 />
 <Line
 dataKey="predicted"
 name="Прогноза"
 stroke={c.primary}
 strokeWidth={2.5}
 strokeDasharray="6 4"
 dot={{ r: 3 }}
 connectNulls
 isAnimationActive={false}
 />
 </ComposedChart>
 </ResponsiveContainer>
 </div>
 </figure>
 );
}
