"use client";

import { useCallback, useEffect, useState } from "react";

import {
 Alert,
 Badge,
 Button,
 Card,
 CardContent,
 CardHeader,
 CardTitle,
 Skeleton,
} from "@/components/ui";
import { api, type NewsFeed, type NewsImpact } from "@/lib/api";
import { LargeTitle } from "@/components/large-title";
import { cn, relativeTime } from "@/lib/utils";

const IMPACT: Record<
 NewsImpact,
 { dot: string; tone: "good" | "warn" | "bad"; label: string }
> = {
 FAVOURABLE: {
 dot: "bg-good",
 tone: "good",
 label: "Благоприятно за вноската",
 },
 NEUTRAL: { dot: "bg-label-tertiary", tone: "warn", label: "Без ясна посока" },
 UNFAVOURABLE: {
 dot: "bg-bad",
 tone: "bad",
 label: "Неблагоприятно за вноската",
 },
};

export default function NewsPage() {
 const [feed, setFeed] = useState<NewsFeed | null>(null);
 const [bulgariaOnly, setBulgariaOnly] = useState(false);
 const [error, setError] = useState<string | null>(null);
 const [loading, setLoading] = useState(true);

 const load = useCallback((onlyBg: boolean) => {
 setLoading(true);
 api
 .news(onlyBg)
 .then(setFeed)
 .catch((e: Error) => setError(e.message))
 .finally(() => setLoading(false));
 }, []);

 useEffect(() => {
 load(bulgariaOnly);
 }, [load, bulgariaOnly]);

 if (loading && !feed) return <Skeleton className="h-96 w-full" />;
 if (error) return <Alert tone="bad">{error}</Alert>;
 if (!feed) return null;

 return (
 <div className="cascade space-y-4">
 <LargeTitle
        title="Икономиката на прост език"
        description="Новини от ЕЦБ, Европейската комисия и български издания, подредени по това какво означават за вноската ви."
      />

 <Card>
 <CardContent className="pt-5">
 <div className="flex flex-wrap items-center justify-between gap-3">
 <div>
 <div className="type-subhead font-medium">
 {feed.aggregate_label_bg}
 </div>
 <div className="mt-1 type-caption text-muted-foreground">
 {feed.aggregate_sentiment !== null
 ? `Обобщен тон: ${feed.aggregate_sentiment.toFixed(2)} (−1 = натиск нагоре, +1 = натиск надолу)`
 : "Няма достатъчно новини с ясен сигнал за оценка."}
 {!feed.translator_available &&
 " · Преводачът е изключен, чуждите заглавия се показват в оригинал."}
 </div>
 </div>
 <Button
 variant={bulgariaOnly ? "default" : "outline"}
 size="sm"
 onClick={() => setBulgariaOnly((v) => !v)}
 >
 {bulgariaOnly ? "Показвам само за България" : "Само за България"}
 </Button>
 </div>
 </CardContent>
 </Card>

 {feed.items.length === 0 && (
 <Alert>
 Няма новини по темата в момента. Пуснете{" "}
 <code className="type-caption">python -m scripts.ingest_news</code>, за да
 заредите последните.
 </Alert>
 )}

 <div className="space-y-3">
 {feed.items.map((item) => {
 const impact = IMPACT[item.impact];
 return (
 <Card key={item.id}>
 <CardHeader className="pb-2">
 <div className="flex items-start gap-3">
 <span
 className={cn("mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full", impact.dot)}
 aria-hidden
 />
 <div className="min-w-0 flex-1">
 <CardTitle className="type-body leading-snug">
 <a
 href={item.url}
 target="_blank"
 rel="noopener noreferrer"
 className="hover:underline"
 >
 {item.title_bg}
 </a>
 </CardTitle>
 <div className="mt-1.5 flex flex-wrap items-center gap-2 type-caption text-muted-foreground">
 <span>{item.source_name}</span>
 <span>·</span>
 <span>{relativeTime(item.published_at)}</span>
 {item.is_bulgaria_related && (
 <Badge tone="warn">България</Badge>
 )}
 {item.was_translated && (
 <span className="type-caption">преведено автоматично</span>
 )}
 </div>
 </div>
 </div>
 </CardHeader>
 <CardContent className="pt-1">
 <div
 className={cn(
 "rounded-xl p-3 type-subhead leading-relaxed",
 item.impact === "UNFAVOURABLE"
 ? "bg-bad/10 text-bad"
 : item.impact === "FAVOURABLE"
 ? "bg-good/10 text-good"
 : "bg-muted text-muted-foreground",
 )}
 >
 <div className="mb-1 type-caption font-semibold uppercase tracking-wide">
 Какво означава това за моя джоб?
 </div>
 {item.wallet_explanation_bg}
 </div>

 {item.was_translated && (
 <details className="mt-2">
 <summary className="cursor-pointer type-caption text-muted-foreground">
 Оригинално заглавие
 </summary>
 <p className="mt-1 type-caption text-muted-foreground">
 {item.title_original}
 </p>
 </details>
 )}
 </CardContent>
 </Card>
 );
 })}
 </div>
 </div>
 );
}
