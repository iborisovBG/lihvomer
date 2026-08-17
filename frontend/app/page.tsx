"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AnswerHero } from "@/components/answer-hero";
import { ForecastChart } from "@/components/forecast-chart";
import { KpiGrid } from "@/components/kpi-grid";
import { RiskGauge } from "@/components/risk-gauge";
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
 getToken,
 type Forecast,
 type LiveDashboard,
 type LoanProjection,
} from "@/lib/api";
import { cn, formatDate, money, percent, signedMoney } from "@/lib/utils";

function PaymentCard({ projection }: { projection: LoanProjection }) {
 const ninety = projection.horizons.find((h) => h.horizon_days === 90);
 if (!ninety) return null;

 const delta = ninety.delta_monthly;
 const rising = delta > 0.5;
 const falling = delta < -0.5;

 return (
 <Card>
 <CardHeader>
 <div className="flex items-start justify-between gap-3">
 <div>
 <CardTitle>{projection.label}</CardTitle>
 <CardDescription>
 {projection.bank_name} · {percent(projection.current_rate_pct)}
 </CardDescription>
 </div>
 <Badge tone={rising ? "bad" : falling ? "good" : "neutral"}>
 {rising ? "Расте" : falling ? "Пада" : "Стабилно"}
 </Badge>
 </div>
 </CardHeader>
 <CardContent>
 <div className="grid grid-cols-2 gap-4">
 <div>
 <div className="type-caption text-muted-foreground">Сега плащате</div>
 <div className="mt-1 type-title-1 tabular-nums">
 {money(projection.current_monthly_payment, projection.currency)}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 След 3 месеца (прогноза)
 </div>
 <div
 className={cn(
 "mt-1 type-title-1 tabular-nums",
 rising && "text-bad",
 falling && "text-good",
 )}
 >
 {money(ninety.projected_monthly_payment, projection.currency)}
 </div>
 </div>
 </div>

 <div
 className={cn(
 "mt-4 rounded-xl p-3 type-subhead font-medium",
 rising
 ? "bg-bad/10 text-bad"
 : falling
 ? "bg-good/10 text-good"
 : "bg-muted text-muted-foreground",
 )}
 >
 {Math.abs(delta) < 0.5 ? (
 "Вноската ви остава практически същата."
 ) : (
 <>
 Вноската ви ще се промени с{" "}
 <strong>{signedMoney(delta, projection.currency)}</strong> на
 месец
 {projection.currency === "BGN" && (
 <> ({signedMoney(ninety.delta_monthly_eur, "EUR")} след
 преизчисляване в евро)</>
 )}
 .
 </>
 )}
 </div>

 {projection.rate_consistency_warning_bg && (
 <div className="mt-3 rounded-xl border border-warn/30 bg-warn/10 p-3 type-caption leading-relaxed text-warn">
 <strong>Проверете надбавката.</strong>{" "}
 {projection.rate_consistency_warning_bg}
 </div>
 )}

 <details className="mt-3">
 <summary className="cursor-pointer type-caption font-medium text-primary">
 Как е сметнато това?
 </summary>
 <p className="mt-2 type-caption leading-relaxed text-muted-foreground">
 {projection.explanation_bg}
 </p>
 <p className="mt-2 type-caption text-muted-foreground">
 При най-неблагоприятния сценарий вноската може да стигне{" "}
 {money(ninety.ci_upper_payment, projection.currency)}, а при
 най-благоприятния —{" "}
 {money(ninety.ci_lower_payment, projection.currency)}.
 </p>
 </details>
 </CardContent>
 </Card>
 );
}

export default function DashboardPage() {
 const [dashboard, setDashboard] = useState<LiveDashboard | null>(null);
 const [forecast, setForecast] = useState<Forecast | null>(null);
 const [projections, setProjections] = useState<LoanProjection[]>([]);
 const [error, setError] = useState<string | null>(null);
 const [loading, setLoading] = useState(true);
 const [signedIn, setSignedIn] = useState(false);

 useEffect(() => {
 const hasToken = getToken() !== null;
 setSignedIn(hasToken);

 Promise.all([api.dashboard(), api.forecast()])
 .then(([dashboardData, forecastData]) => {
 setDashboard(dashboardData);
 setForecast(forecastData);
 })
 .catch((err: Error) => setError(err.message))
 .finally(() => setLoading(false));

 if (hasToken) {
 api.projections().then(setProjections).catch(() => setProjections([]));
 }
 }, []);

 if (loading) {
 return (
 <div className="space-y-4">
 <Skeleton className="h-64 w-full" />
 <Skeleton className="h-40 w-full" />
 </div>
 );
 }

 if (error) {
 return <Alert tone="bad">{error}</Alert>;
 }

 return (
 <div className="cascade space-y-8">
 <AnswerHero
 projections={projections}
 score={dashboard?.score ?? null}
 signedIn={signedIn}
 />

 <div id="detail" className="scroll-mt-20">
 <h2 className="type-title-3">Защо това число</h2>
 <p className="mt-1 type-subhead text-muted-foreground">
 Оценката се сглобява от четири показателя с различна тежест.
 </p>
 </div>

 <section className="grid gap-4 lg:grid-cols-[minmax(0,340px)_1fr]">
 <Card>
 <CardHeader>
 <CardTitle>Тахометър на риска</CardTitle>
 </CardHeader>
 <CardContent>
 {dashboard?.score ? (
 <RiskGauge score={dashboard.score} />
 ) : (
 <p className="type-subhead text-muted-foreground">
 Оценката не може да бъде изчислена — липсват част от данните.
 </p>
 )}
 </CardContent>
 </Card>

 <Card>
 <CardHeader>
 <CardTitle>Какво стои зад оценката</CardTitle>
 <CardDescription>
 Всеки показател тежи различно в крайния резултат.
 </CardDescription>
 </CardHeader>
 <CardContent className="space-y-3">
 {dashboard?.score &&
 Object.entries(dashboard.score.components).map(([key, part]) => (
 <div key={key}>
 <div className="flex items-baseline justify-between gap-2">
 <span className="type-subhead font-medium">{part.label_bg}</span>
 <span className="shrink-0 type-caption text-muted-foreground">
 тежест {Math.round(part.weight * 100)}%
 </span>
 </div>
 <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-muted">
 <div
 className={cn(
 "h-full rounded-full",
 part.points >= 70
 ? "bg-good"
 : part.points >= 40
 ? "bg-warn"
 : "bg-bad",
 )}
 style={{ width: `${part.points}%` }}
 />
 </div>
 <p className="mt-1.5 type-caption leading-relaxed text-muted-foreground">
 {part.explanation_bg}
 </p>
 </div>
 ))}
 </CardContent>
 </Card>
 </section>

 {signedIn && projections.length > 0 && (
 <section>
 <h2 className="mb-1 type-title-3">Моята вноска</h2>
 <p className="mb-3 type-subhead text-muted-foreground">
 Колко плащате сега и колко се очаква да плащате след три месеца.
 </p>
 <div className="grid gap-4 md:grid-cols-2">
 {projections.map((projection) => (
 <PaymentCard key={projection.loan_id} projection={projection} />
 ))}
 </div>
 </section>
 )}

 {signedIn && projections.length === 0 && (
 <Alert>
 Още нямате въведени кредити.{" "}
 <Link href="/loans" className="font-medium text-primary underline">
 Добавете кредит
 </Link>
 , за да виждате как се променя точно вашата вноска.
 </Alert>
 )}

 {!signedIn && (
 <Alert>
 <Link href="/login" className="font-medium text-primary underline">
 Влезте в профила си
 </Link>
 , за да следите как се променя вноската по вашия конкретен кредит.
 </Alert>
 )}

 <section>
 <h2 className="mb-1 type-title-3">Числата в момента</h2>
 <p className="mb-3 type-subhead text-muted-foreground">
 Подредени по въпроса, на който отговарят. Натиснете за обяснение.
 </p>
 {dashboard && (
 <KpiGrid
 indicators={dashboard.indicators}
 realRate={dashboard.real_mortgage_rate_pct}
 />
 )}
 </section>

 {forecast && (
 <Card>
 <CardHeader>
 <CardTitle>
 Лихвите в България спрямо европейските, с прогноза
 </CardTitle>
 <CardDescription>
 Последно отчетено:{" "}
 {percent(forecast.latest_actual_value)} към{" "}
 {formatDate(forecast.latest_actual_date)}
 </CardDescription>
 </CardHeader>
 <CardContent>
 <ForecastChart forecast={forecast} />

 <p className="mt-4 type-subhead leading-relaxed text-muted-foreground">
 {forecast.explanation_bg}
 </p>

 <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
 {forecast.points.map((point) => (
 <div
 key={point.horizon_days}
 className="rounded-xl border border-border p-3"
 >
 <div className="type-caption text-muted-foreground">
 след {point.horizon_days} дни
 </div>
 <div className="mt-1 type-title-3 tabular-nums">
 {percent(point.predicted_value)}
 </div>
 <div className="type-caption text-muted-foreground">
 {percent(point.ci_lower)} – {percent(point.ci_upper)}
 </div>
 </div>
 ))}
 </div>

 <details className="mt-4">
 <summary className="cursor-pointer type-caption font-medium text-primary">
 Показатели на модела
 </summary>
 <dl className="mt-2 grid grid-cols-2 gap-2 type-caption text-muted-foreground sm:grid-cols-4">
 <div>
 <dt>Обяснена промяна</dt>
 <dd className="font-semibold text-foreground">
 {(forecast.r_squared * 100).toFixed(0)}%
 </dd>
 </div>
 <div>
 <dt>Закъснение</dt>
 <dd className="font-semibold text-foreground">
 {forecast.best_lag_days} дни
 </dd>
 </div>
 <div>
 <dt>Наблюдения</dt>
 <dd className="font-semibold text-foreground">
 {forecast.n_obs}
 </dd>
 </div>
 <div>
 <dt>Драйвер</dt>
 <dd className="font-semibold text-foreground">
 {forecast.driver_series_code}
 </dd>
 </div>
 </dl>
 </details>
 </CardContent>
 </Card>
 )}
 </div>
 );
}
