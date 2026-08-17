"use client";

import { useEffect, useState } from "react";

import { SpreadChart } from "@/components/spread-chart";
import {
 Alert,
 Badge,
 Card,
 CardContent,
 CardDescription,
 CardHeader,
 CardTitle,
 Skeleton,
} from "@/components/ui";
import {
 api,
 type Fiscal,
 type Freshness,
 type Spending,
 type SpreadStatus,
} from "@/lib/api";
import { LargeTitle } from "@/components/large-title";
import { cn, percent, quarterLabel } from "@/lib/utils";

const SPREAD_TONE: Record<SpreadStatus, { tone: "good" | "warn" | "bad" | "neutral"; label: string }> = {
 CALM: { tone: "good", label: "Спокойно" },
 WATCH: { tone: "warn", label: "За наблюдение" },
 ALERT: { tone: "bad", label: "Повишен риск" },
 UNKNOWN: { tone: "neutral", label: "Няма данни" },
};

function LimitBar({
 value,
 limit,
 invert = false,
}: {
 value: number;
 limit: number;
 invert?: boolean;
}) {
 // При дефицита и двете числа са отрицателни, затова сравняваме модулите.
 const magnitude = Math.abs(value);
 const cap = Math.abs(limit);
 const fill = Math.min(100, (magnitude / Math.max(cap * 2, magnitude)) * 100);
 const limitAt = Math.min(100, (cap / Math.max(cap * 2, magnitude)) * 100);
 const breached = invert ? magnitude > cap : value > limit;

 return (
 <div className="relative mt-2 h-3 w-full overflow-hidden rounded-full bg-muted">
 <div
 className={cn(
 "h-full rounded-full",
 breached ? "bg-bad" : "bg-good",
 )}
 style={{ width: `${fill}%` }}
 />
 <div
 className="absolute top-0 h-full w-0.5 bg-foreground/70"
 style={{ left: `${limitAt}%` }}
 title={`Праг ${cap}%`}
 />
 </div>
 );
}

export default function StatePage() {
 const [fiscal, setFiscal] = useState<Fiscal | null>(null);
 const [spending, setSpending] = useState<Spending | null>(null);
 const [freshness, setFreshness] = useState<Freshness[]>([]);
 const [error, setError] = useState<string | null>(null);
 const [loading, setLoading] = useState(true);

 useEffect(() => {
 Promise.all([api.fiscal(), api.freshness()])
 .then(([f, fr]) => {
 setFiscal(f);
 setFreshness(fr);
 })
 .catch((e: Error) => setError(e.message))
 .finally(() => setLoading(false));

 api.spending().then(setSpending).catch(() => setSpending(null));
 }, []);

 if (loading) return <Skeleton className="h-96 w-full" />;
 if (error) return <Alert tone="bad">{error}</Alert>;
 if (!fiscal) return null;

 const stale = freshness.filter((f) => f.is_stale);
 const spreadTone = SPREAD_TONE[fiscal.spread_status];
 const maxLine = spending
 ? Math.max(...spending.lines.filter((l) => !l.is_detail).map((l) => l.pct_gdp))
 : 0;

 return (
 <div className="cascade space-y-6">
 <LargeTitle
        title="Държавата и вашият кредит"
        description="Бюджетът на държавата не е абстракция — той стига до вноската ви през цената, на която България взема заеми."
      />

 {stale.length > 0 && (
 <Alert>
 <strong>Част от данните са застояли.</strong>{" "}
 {stale
 .map((f) => `${f.name_bg} (${f.age_days} дни)`)
 .slice(0, 3)
 .join("; ")}
 . Показваме последното официално публикувано, а не прогноза.
 </Alert>
 )}

 <section className="grid gap-4 md:grid-cols-2">
 <Card>
 <CardHeader>
 <CardTitle>Държавен дълг</CardTitle>
 <CardDescription>
 {fiscal.debt_is_quarterly ? "тримесечни" : "годишни"} данни към{" "}
 {quarterLabel(fiscal.debt_period, fiscal.debt_is_quarterly)}
 </CardDescription>
 </CardHeader>
 <CardContent>
 <div className="flex items-baseline gap-3">
 <span className="type-large-title tabular-nums">
 {percent(fiscal.debt_pct_gdp, 1)}
 </span>
 <Badge tone={fiscal.exceeds_debt_limit ? "bad" : "good"}>
 {fiscal.exceeds_debt_limit ? "над тавана" : "под тавана"}
 </Badge>
 </div>
 {fiscal.debt_pct_gdp !== null && (
 <LimitBar value={fiscal.debt_pct_gdp} limit={fiscal.debt_limit_pct} />
 )}
 <p className="mt-2 type-caption text-muted-foreground">
 Европейският таван е {fiscal.debt_limit_pct}% от икономиката.
 Ниският дълг е буферът, който държи лихвите ви ниски.
 </p>
 </CardContent>
 </Card>

 <Card>
 <CardHeader>
 <CardTitle>Бюджетен дефицит</CardTitle>
 <CardDescription>
 {fiscal.deficit_is_quarterly ? "тримесечни" : "годишни"} данни към{" "}
 {quarterLabel(fiscal.deficit_period, fiscal.deficit_is_quarterly)}
 </CardDescription>
 </CardHeader>
 <CardContent>
 <div className="flex items-baseline gap-3">
 <span
 className={cn(
 "type-large-title tabular-nums",
 fiscal.exceeds_deficit_limit &&
 "text-bad",
 )}
 >
 {percent(fiscal.deficit_pct_gdp, 1)}
 </span>
 <Badge tone={fiscal.exceeds_deficit_limit ? "bad" : "good"}>
 {fiscal.exceeds_deficit_limit
 ? "над европейския праг"
 : "в рамките на прага"}
 </Badge>
 </div>
 {fiscal.deficit_pct_gdp !== null && (
 <LimitBar
 value={fiscal.deficit_pct_gdp}
 limit={fiscal.deficit_limit_pct}
 invert
 />
 )}
 <p className="mt-2 type-caption text-muted-foreground">
 Прагът по европейските правила е {fiscal.deficit_limit_pct}% от
 икономиката. Трайното му надхвърляне води до наказателна
 процедура.
 </p>
 </CardContent>
 </Card>
 </section>

 <Card>
 <CardHeader>
 <div className="flex flex-wrap items-start justify-between gap-3">
 <div>
 <CardTitle>
 Колко по-скъпо взема заеми България спрямо Германия
 </CardTitle>
 <CardDescription>
 Разликата в доходността по 10-годишните облигации, в базисни
 точки. 100 базисни точки = 1 процентен пункт.
 </CardDescription>
 </div>
 <div className="text-right">
 <div className="type-title-1 tabular-nums">
 {fiscal.spread_latest_bp?.toFixed(0) ?? "—"}
 <span className="ml-1 type-subhead font-normal text-muted-foreground">
 б.т.
 </span>
 </div>
 <Badge tone={spreadTone.tone}>{spreadTone.label}</Badge>
 </div>
 </div>
 </CardHeader>
 <CardContent>
 {fiscal.spread_history.length > 0 ? (
 <SpreadChart
 history={fiscal.spread_history}
 watchBp={fiscal.spread_watch_bp}
 alertBp={fiscal.spread_alert_bp}
 />
 ) : (
 <Alert>Няма достатъчно данни за спреда.</Alert>
 )}
 <p className="mt-4 type-subhead leading-relaxed text-muted-foreground">
 {fiscal.explanation_bg}
 </p>
 <div className="mt-3 rounded-xl bg-muted p-3 type-caption leading-relaxed text-muted-foreground">
 <strong className="text-foreground">Защо това е ранен сигнал:</strong>{" "}
 когато спредът се разшири трайно, банките първо вдигат лихвите по
 потребителските и бизнес кредитите, и едва накрая по ипотечните.
 Промяната стига до вноската ви месеци след като се е появила тук.
 </div>
 </CardContent>
 </Card>

 {spending && (
 <Card>
 <CardHeader>
 <CardTitle>Къде отиват парите на държавата</CardTitle>
 <CardDescription>
 {spending.period} г. · общо {percent(spending.total_pct_gdp, 1)} от
 икономиката · източник: {spending.source_ref}
 </CardDescription>
 </CardHeader>
 <CardContent>
 <div className="space-y-2.5">
 {spending.lines
 .filter((line) => !line.is_detail)
 .map((line) => (
 <div key={line.cofog_code}>
 <div className="flex items-baseline justify-between gap-2 type-subhead">
 <span className="font-medium">{line.label_bg}</span>
 <span className="shrink-0 tabular-nums text-muted-foreground">
 {line.pct_gdp.toFixed(1).replace(".", ",")}% от БВП ·{" "}
 {line.share_of_total_pct.toFixed(0)}% от бюджета
 </span>
 </div>
 <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
 <div
 className="h-full rounded-full bg-primary"
 style={{ width: `${(line.pct_gdp / maxLine) * 100}%` }}
 />
 </div>
 </div>
 ))}
 </div>

 {spending.lines.some((line) => line.is_detail) && (
 <div className="mt-4 border-t border-border pt-3">
 <div className="mb-2 type-caption font-medium text-muted-foreground">
 Разбивка на най-големите пера
 </div>
 <div className="grid gap-1.5 sm:grid-cols-2">
 {spending.lines
 .filter((line) => line.is_detail)
 .map((line) => (
 <div
 key={line.cofog_code}
 className="flex justify-between type-caption"
 >
 <span className="text-muted-foreground">
 {line.label_bg}
 </span>
 <span className="tabular-nums font-medium">
 {line.pct_gdp.toFixed(1).replace(".", ",")}%
 </span>
 </div>
 ))}
 </div>
 </div>
 )}

 <p className="mt-4 type-subhead leading-relaxed text-muted-foreground">
 {spending.explanation_bg}
 </p>
 </CardContent>
 </Card>
 )}
 </div>
 );
}
