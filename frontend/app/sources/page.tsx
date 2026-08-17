"use client";

import { useEffect, useState } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";

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
import { AutomationStatus } from "@/components/automation-status";
import { api, type Sources } from "@/lib/api";
import { formatDate } from "@/lib/utils";

const FREQUENCY_BG: Record<string, string> = {
 DAILY: "всеки работен ден",
 MONTHLY: "месечно",
 QUARTERLY: "тримесечно",
 ANNUAL: "годишно",
};

export default function SourcesPage() {
 const [sources, setSources] = useState<Sources | null>(null);
 const [error, setError] = useState<string | null>(null);

 useEffect(() => {
 api
 .sources()
 .then(setSources)
 .catch((e: Error) => setError(e.message));
 }, []);

 if (error) return <Alert tone="bad">{error}</Alert>;
 if (!sources) return <Skeleton className="h-96 w-full" />;

 const totalSeries = sources.providers.reduce(
 (sum, p) => sum + p.series.length,
 0,
 );

 return (
 <div className="cascade space-y-6">
 <div>
 <h1 className="type-title-1">Откъде идва всяко число</h1>
 <p className="mt-2 max-w-prose type-subhead leading-relaxed text-muted-foreground">
 Приложението не използва измислени или примерни данни. Всички{" "}
 {totalSeries} показателя се теглят автоматично от официалните
 интерфейси на институциите по-долу. Всеки ред има линк, на който
 можете да проверите числото сами.
 </p>
 </div>

 <Card className="border-primary/30 bg-accent">
 <CardContent className="flex gap-3 pt-5">
 <ShieldCheck
 className="mt-0.5 h-5 w-5 shrink-0 text-primary"
 aria-hidden
 />
 <p className="type-subhead leading-relaxed">{sources.disclaimer_bg}</p>
 </CardContent>
 </Card>

 <AutomationStatus />

 {sources.providers.map((provider) => (
 <Card key={provider.key}>
 <CardHeader>
 <div className="flex flex-wrap items-start justify-between gap-2">
 <div>
 <CardTitle className="type-title-3">{provider.name_bg}</CardTitle>
 <CardDescription className="max-w-prose">
 {provider.description_bg}
 </CardDescription>
 </div>
 <a
 href={provider.portal_url}
 target="_blank"
 rel="noopener noreferrer"
 className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-border px-3 py-1.5 type-caption font-medium transition-colors hover:bg-muted"
 >
 Портал <ExternalLink className="h-3 w-3" />
 </a>
 </div>
 </CardHeader>
 <CardContent>
 <div className="mb-3 rounded-lg bg-muted p-2.5 font-mono type-caption leading-relaxed text-muted-foreground">
 <span className="select-all break-all">
 {provider.api_base_url}
 </span>
 </div>

            <div className="list-group border border-border/60">
              {provider.series.map((series) => (
                <div
                  key={series.code}
                  className="list-row flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3"
                >
                  <div className="min-w-[12rem] flex-1">
                    <div className="type-subhead font-medium leading-snug">
                      {series.name_bg}
                    </div>
                    <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                      {series.source_ref}
                    </div>
                    {series.superseded_by && (
                      <Badge tone="neutral" className="mt-1">
                        прекратен — вече се следи в евро
                      </Badge>
                    )}
                  </div>

                  <div className="shrink-0 text-right">
                    <div className="type-caption text-muted-foreground">
                      {FREQUENCY_BG[series.frequency] ?? series.frequency}
                    </div>
                    <div className="type-caption tabular-nums text-muted-foreground">
                      {series.latest_date
                        ? formatDate(series.latest_date)
                        : "не е зареден"}
                    </div>
                  </div>

                  <a
                    href={series.browse_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="press shrink-0 rounded-lg bg-muted px-2.5 py-1.5 type-caption font-medium text-primary"
                  >
                    провери
                  </a>
                </div>
              ))}
            </div>

 <p className="mt-3 type-caption text-muted-foreground">
 Условия за ползване: {provider.licence_bg}
 </p>
 </CardContent>
 </Card>
 ))}

 <Card>
 <CardHeader>
 <CardTitle className="type-title-3">Новинарски източници</CardTitle>
 <CardDescription>
 Заглавията се теглят от публичните RSS емисии на изданията.
 Чуждоезичните се превеждат автоматично с отворен модел, който работи
 локално — нищо не се изпраща към платена услуга.
 </CardDescription>
 </CardHeader>
 <CardContent>
 <ul className="grid gap-2 sm:grid-cols-2">
 {sources.news_feeds.map((feed) => (
 <li key={feed.code} className="flex items-center gap-2 type-subhead">
 <Badge tone="neutral">
 {feed.language === "bg" ? "БГ" : "EN"}
 </Badge>
 <a
 href={feed.url}
 target="_blank"
 rel="noopener noreferrer"
 className="text-muted-foreground hover:text-primary hover:underline"
 >
 {feed.name_bg}
 </a>
 </li>
 ))}
 </ul>
 </CardContent>
 </Card>
 </div>
 );
}
