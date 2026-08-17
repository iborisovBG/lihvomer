"use client";

import {
 Area,
 CartesianGrid,
 ComposedChart,
 Legend,
 ReferenceLine,
 ResponsiveContainer,
 Tooltip,
 XAxis,
 YAxis,
} from "recharts";

import type { SpreadPoint } from "@/lib/api";
import { useThemeColors } from "@/lib/use-theme-colors";
import { shortDate } from "@/lib/utils";

export function SpreadChart({
 history,
 watchBp,
 alertBp,
}: {
 history: SpreadPoint[];
 watchBp: number;
 alertBp: number;
}) {
  const c = useThemeColors();

 return (
 <div className="h-[280px] w-full">
 <ResponsiveContainer width="100%" height="100%">
 <ComposedChart
 data={history}
 margin={{ top: 8, right: 8, bottom: 4, left: -16 }}
 >
 <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
 <XAxis
 dataKey="period"
 tickFormatter={shortDate}
 tick={{ fontSize: 11, fill: c.muted }}
 minTickGap={30}
 />
 <YAxis
 tick={{ fontSize: 11, fill: c.muted }}
 tickFormatter={(v: number) => `${v.toFixed(0)}`}
 domain={["auto", "auto"]}
 label={{
 value: "базисни точки",
 angle: -90,
 position: "insideLeft",
 style: { fontSize: 11, fill: c.muted },
 }}
 />
 <Tooltip
 labelFormatter={(label) =>
 typeof label === "string" ? shortDate(label) : ""
 }
 formatter={(value, name) => [
 `${Number(value).toFixed(0)} б.т.`,
 String(name),
 ]}
 contentStyle={{
 borderRadius: 12,
 border: "1px solid hsl(var(--border))",
 background: "hsl(var(--card))",
 fontSize: 12,
 }}
 />
 <Legend wrapperStyle={{ fontSize: 12 }} />
 <ReferenceLine
 y={watchBp}
 stroke={c.warn}
 strokeDasharray="5 4"
 label={{
 value: `${watchBp} б.т. — внимание`,
 position: "insideTopRight",
 style: { fontSize: 10, fill: c.warn },
 }}
 />
 <ReferenceLine
 y={alertBp}
 stroke={c.bad}
 strokeDasharray="5 4"
 label={{
 value: `${alertBp} б.т. — тревога`,
 position: "insideTopRight",
 style: { fontSize: 10, fill: c.bad },
 }}
 />
 <Area
 dataKey="spread_bp"
 name="Спред България − Германия"
 stroke={c.primary}
 strokeWidth={2}
 fill={c.primary}
 fillOpacity={0.18}
 isAnimationActive={false}
 />
 </ComposedChart>
 </ResponsiveContainer>
 </div>
 );
}
