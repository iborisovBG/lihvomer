"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import type { LoanProjection, Score } from "@/lib/api";
import { cn, money, signedMoney } from "@/lib/utils";

/**
 * Таблото започва с отговор, не с данни.
 *
 * Човек, който отваря приложението за трети път, иска да знае едно нещо:
 * променя ли се вноската му. Числото е отговорът, а не съдържанието —
 * обяснението и показателите стоят под него за тези, които искат да проверят.
 */

const SIGNAL_COPY: Record<Score["signal"], { line: string; tone: string }> = {
 TAKE: {
 line: "Моментът е благоприятен за нов кредит",
 tone: "text-good",
 },
 NEUTRAL: {
 line: "Няма ясен сигнал нито за бързане, нито за изчакване",
 tone: "text-warn",
 },
 WAIT: {
 line: "Показателите сочат натиск нагоре върху лихвите",
 tone: "text-bad",
 },
};

function Shell({ children }: { children: React.ReactNode }) {
 return (
 <section
 aria-labelledby="answer-heading"
 className="glass glass-specular rounded-[1.5rem] bg-gradient-to-br from-accent/70 to-surface/30 p-6 md:p-10"
 >
 {children}
 </section>
 );
}

export function AnswerHero({
 projections,
 score,
 signedIn,
}: {
 projections: LoanProjection[];
 score: Score | null;
 signedIn: boolean;
}) {
 // Има кредит: отговорът е неговата вноска.
 const withForecast = projections
 .map((p) => ({ p, h: p.horizons.find((x) => x.horizon_days === 90) }))
 .filter((x) => x.h !== undefined) as {
 p: LoanProjection;
 h: NonNullable<LoanProjection["horizons"][number]>;
 }[];

 if (signedIn && withForecast.length > 0) {
 const totalDelta = withForecast.reduce((sum, x) => sum + x.h.delta_monthly_eur, 0);
 const rising = totalDelta > 0.5;
 const falling = totalDelta < -0.5;
 const single = withForecast.length === 1 ? withForecast[0] : null;

 return (
 <Shell>
 <p className="type-subhead font-medium text-label-secondary">
 {single
 ? `Вноската по „${single.p.label}“ след 3 месеца`
 : `Вноските по ${withForecast.length} кредита след 3 месеца`}
 </p>

 <p
 id="answer-heading"
 className={cn(
 "mt-2 type-large-title tabular-nums md:text-[3.5rem] md:leading-none",
 rising && "text-bad",
 falling && "text-good",
 )}
 >
 {Math.abs(totalDelta) < 0.5
 ? "Без промяна"
 : `${signedMoney(totalDelta, "EUR")}`}
 {Math.abs(totalDelta) >= 0.5 && (
 <span className="ml-2 type-title-3 font-normal text-label-secondary">
 на месец
 </span>
 )}
 </p>

 {single && (
 <p className="mt-3 type-body text-label-secondary">
 От {money(single.p.current_monthly_payment, single.p.currency)} на{" "}
 <strong className="text-foreground">
 {money(single.h.projected_monthly_payment, single.p.currency)}
 </strong>{" "}
 в {single.p.bank_name}.
 </p>
 )}

 <p className="mt-4 max-w-xl type-subhead leading-relaxed text-label-secondary">
 {rising
 ? "Прогнозата се основава на очакваната промяна в индекса по вашия договор. Ако имате дата на преоценка, вноската не мърда до нея."
 : falling
 ? "Прогнозата се основава на очакваната промяна в индекса по вашия договор."
 : "При текущите прогнози вноската ви остава практически същата."}
 </p>

 <div className="mt-6 flex flex-wrap gap-3">
 <Link
 href="/health"
 className="press inline-flex h-11 items-center gap-2 rounded-[0.875rem] bg-primary px-5 type-callout font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none"
 >
 Добре ли съм спрямо пазара
 <ArrowRight className="h-4 w-4" aria-hidden />
 </Link>
 <a
 href="#detail"
 className="press inline-flex h-11 items-center rounded-[0.875rem] bg-muted px-5 type-callout font-semibold transition-colors hover:bg-muted/70 focus-visible:outline-none"
 >
 Защо това число?
 </a>
 </div>
 </Shell>
 );
 }

 // Няма кредит: отговорът е оценката на момента.
 const copy = score ? SIGNAL_COPY[score.signal] : null;

 return (
 <Shell>
 <p className="type-subhead font-medium text-label-secondary">
 Подходящ ли е моментът за кредит
 </p>

 <p
 id="answer-heading"
 className={cn(
 "mt-2 type-large-title tabular-nums md:text-[3.5rem] md:leading-none",
 copy?.tone,
 )}
 >
 {score ? Math.round(score.score) : "—"}
 <span className="ml-1 type-title-2 font-normal text-label-secondary">
 /100
 </span>
 </p>

 <p className="mt-3 max-w-xl type-body text-label-secondary">
 {copy?.line ?? "Оценката не може да бъде изчислена — липсват данни."}
 </p>

 <div className="mt-6 flex flex-wrap gap-3">
 {signedIn ? (
 <Link
 href="/loans"
 className="press inline-flex h-11 items-center gap-2 rounded-[0.875rem] bg-primary px-5 type-callout font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none"
 >
 Добавете кредит
 <ArrowRight className="h-4 w-4" aria-hidden />
 </Link>
 ) : (
 <Link
 href="/login"
 className="press inline-flex h-11 items-center gap-2 rounded-[0.875rem] bg-primary px-5 type-callout font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none"
 >
 Вижте какво значи за вашия кредит
 <ArrowRight className="h-4 w-4" aria-hidden />
 </Link>
 )}
 <a
 href="#detail"
 className="press inline-flex h-11 items-center rounded-[0.875rem] bg-muted px-5 type-callout font-semibold transition-colors hover:bg-muted/70 focus-visible:outline-none"
 >
 Защо това число?
 </a>
 </div>
 </Shell>
 );
}
