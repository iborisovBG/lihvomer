"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Clock, XCircle } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui";
import { api, type Automation } from "@/lib/api";
import { relativeTime } from "@/lib/utils";

const JOB_LABELS: Record<string, string> = {
 ingest_macro: "Макроикономически данни",
 ingest_news: "Новини и превод",
 refresh_analytics: "Преизчисляване на прогнозите",
 prune_job_history: "Почистване на историята",
};

export function AutomationStatus() {
 const [data, setData] = useState<Automation | null>(null);

 useEffect(() => {
 api.automation().then(setData).catch(() => setData(null));
 }, []);

 if (!data) return null;

 const lastByName = new Map(data.last_runs.map((r) => [r.job_name, r]));

 return (
 <Card>
 <CardHeader>
 <div className="flex items-center gap-2">
 {data.worker_online ? (
 <CheckCircle2 className="h-5 w-5 text-good" aria-hidden />
 ) : (
 <XCircle className="h-5 w-5 text-warn" aria-hidden />
 )}
 <CardTitle className="type-title-3">Данните се обновяват сами</CardTitle>
 </div>
 <CardDescription>{data.hint_bg}</CardDescription>
 </CardHeader>
 <CardContent>
 <div className="space-y-2">
 {Object.entries(data.schedule_bg).map(([job, schedule]) => {
 const last = lastByName.get(job);
 return (
 <div
 key={job}
 className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-muted px-3 py-2"
 >
 <div className="min-w-0">
 <div className="type-subhead font-medium">
 {JOB_LABELS[job] ?? job}
 </div>
 <div className="flex items-center gap-1 type-caption text-muted-foreground">
 <Clock className="h-3 w-3" aria-hidden />
 {schedule}
 </div>
 </div>
 <div className="text-right type-caption">
 {last ? (
 <>
 <div
 className={
 last.status === "SUCCESS"
 ? "font-medium text-good"
 : last.status === "FAILED"
 ? "font-medium text-bad"
 : "font-medium text-warn"
 }
 >
 {last.status === "SUCCESS"
 ? "успешно"
 : last.status === "FAILED"
 ? "с грешка"
 : "частично"}
 </div>
 <div className="text-muted-foreground">
 {relativeTime(last.started_at)}
 </div>
 </>
 ) : (
 <span className="text-muted-foreground">още не е пускано</span>
 )}
 </div>
 </div>
 );
 })}
 </div>
 </CardContent>
 </Card>
 );
}
