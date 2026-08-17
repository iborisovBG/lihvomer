"use client";

import type { Score } from "@/lib/api";
import { useThemeColors } from "@/lib/use-theme-colors";
import { cn } from "@/lib/utils";

const TONE = {
 TAKE: {
 stroke: "good",
 text: "text-good",
 chip: "bg-good/15 text-good",
 },
 NEUTRAL: {
 stroke: "warn",
 text: "text-warn",
 chip: "bg-warn/15 text-warn",
 },
 WAIT: {
 stroke: "bad",
 text: "text-bad",
 chip: "bg-bad/15 text-bad",
 },
} as const;

const RADIUS = 90;
const CENTER_X = 110;
const CENTER_Y = 108;

function polar(angleDeg: number, radius = RADIUS) {
 const radians = (Math.PI * angleDeg) / 180;
 return {
 x: CENTER_X + radius * Math.cos(radians),
 y: CENTER_Y - radius * Math.sin(radians),
 };
}

function arcPath(fromDeg: number, toDeg: number, radius = RADIUS) {
 const start = polar(fromDeg, radius);
 const end = polar(toDeg, radius);
 const largeArc = Math.abs(toDeg - fromDeg) > 180 ? 1 : 0;
 // Ъглите намаляват отляво надясно, а по екранните оси това е по часовника,
 // затова sweep-флагът е 1.
 return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

/** Стойност 0-100 се нанася върху полукръг от 180° (ляво) до 0° (дясно). */
function angleFor(value: number) {
 return 180 - (Math.min(100, Math.max(0, value)) / 100) * 180;
}

export function RiskGauge({ score }: { score: Score }) {
  const c = useThemeColors();
  const tone = TONE[score.signal];
 const needleAngle = angleFor(score.score);
 const needle = polar(needleAngle, RADIUS - 16);

 return (
 <div className="flex flex-col items-center">
 <svg
 viewBox="0 0 220 130"
 className="w-full max-w-[280px]"
 role="img"
 aria-label={`Оценка на момента: ${score.score} от 100, ${score.signal_label_bg}`}
 >
 <path
 d={arcPath(180, 120)}
 fill="none"
 stroke={c.bad}
 strokeWidth={16}
 strokeLinecap="round"
 opacity={0.25}
 />
 <path
 d={arcPath(120, 54)}
 fill="none"
 stroke={c.warn}
 strokeWidth={16}
 opacity={0.25}
 />
 <path
 d={arcPath(54, 0)}
 fill="none"
 stroke={c.good}
 strokeWidth={16}
 strokeLinecap="round"
 opacity={0.25}
 />
 <path
 d={arcPath(180, needleAngle)}
 fill="none"
 stroke={c[tone.stroke]}
 strokeWidth={16}
 strokeLinecap="round"
 />
 <line
 x1={CENTER_X}
 y1={CENTER_Y}
 x2={needle.x}
 y2={needle.y}
 stroke="currentColor"
 strokeWidth={3}
 strokeLinecap="round"
 className="text-foreground"
 />
 <circle cx={CENTER_X} cy={CENTER_Y} r={7} className="fill-foreground" />
 <text
 x={4}
 y={126}
 className="fill-muted-foreground type-caption"
 textAnchor="start"
 >
 риск
 </text>
 <text
 x={216}
 y={126}
 className="fill-muted-foreground type-caption"
 textAnchor="end"
 >
 добър момент
 </text>
 </svg>

 <div className={cn("type-large-title tabular-nums", tone.text)}>
 {Math.round(score.score)}
 <span className="type-title-1 text-muted-foreground">/100</span>
 </div>
 <span
 className={cn(
 "mt-2 rounded-full px-3 py-1 type-subhead font-semibold",
 tone.chip,
 )}
 >
 {score.signal_label_bg}
 </span>
 <p className="mt-3 text-center type-subhead text-muted-foreground">
 {score.headline_bg}
 </p>
 </div>
 );
}
