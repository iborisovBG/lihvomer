"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { BellRing, RefreshCw } from "lucide-react";

import {
 Alert,
 Badge,
 Button,
 Card,
 CardContent,
 CardDescription,
 CardHeader,
 CardTitle,
 Input,
 Label,
 Skeleton,
} from "@/components/ui";
import {
 api,
 getToken,
 type NotificationFeed,
 type NotificationSeverity,
 type Preferences,
} from "@/lib/api";
import { Segmented, useToast } from "@/components/ios";
import { cn, relativeTime } from "@/lib/utils";

const SEVERITY: Record<
 NotificationSeverity,
 { label: string; tone: "bad" | "good" | "neutral"; ring: string }
> = {
 WARNING: {
 label: "Внимание",
 tone: "bad",
 ring: "border-l-bad",
 },
 OPPORTUNITY: {
 label: "Възможност",
 tone: "good",
 ring: "border-l-good",
 },
 INFO: { label: "Напомняне", tone: "neutral", ring: "border-l-label-tertiary" },
};

function PreferencesPanel({
 emailEnabled,
 onSaved,
}: {
 emailEnabled: boolean;
 onSaved: () => void;
}) {
 const [prefs, setPrefs] = useState<Preferences | null>(null);
 const [busy, setBusy] = useState(false);
 const toast = useToast();

 useEffect(() => {
 api
 .me()
 .then((me) =>
 setPrefs({
 notify_email: me.notify_email,
 notify_push: me.notify_push,
 alert_threshold_eur: me.alert_threshold_eur,
 risk_tolerance: me.risk_tolerance,
 }),
 )
 .catch(() => setPrefs(null));
 }, []);

 if (!prefs) return null;

 async function save(event: React.FormEvent) {
 event.preventDefault();
 if (!prefs) return;
 setBusy(true);
 try {
 await api.savePreferences(prefs);
 toast("Настройките са запазени", "success");
 onSaved();
 } catch (e) {
 toast((e as Error).message, "error");
 } finally {
 setBusy(false);
 }
 }

 return (
 <Card>
 <CardHeader>
 <CardTitle>Кога да ви известяваме</CardTitle>
 <CardDescription>
 Известяваме само когато има конкретна сума и предложено действие — не
 при всяко движение на лихвите.
 </CardDescription>
 </CardHeader>
 <CardContent>
 <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
 <div>
 <Label htmlFor="threshold">
 Праг за известяване (€ на месец)
 </Label>
 <Input
 id="threshold"
 type="number"
 min={0}
 step="any"
 value={prefs.alert_threshold_eur}
 onChange={(e) =>
 setPrefs({
 ...prefs,
 alert_threshold_eur: Number(e.target.value),
 })
 }
 />
 <p className="mt-1 type-caption text-muted-foreground">
 Под тази сума не ви безпокоим.
 </p>
 </div>

 <div>
 <Label htmlFor="risk">Как приемате риска</Label>
 <Segmented
 label="Как приемате риска"
 value={prefs.risk_tolerance}
 onChange={(next) =>
 setPrefs({ ...prefs, risk_tolerance: next })
 }
 options={[
 { value: "CONSERVATIVE", label: "Сигурност" },
 { value: "BALANCED", label: "Балансирано" },
 { value: "AGGRESSIVE", label: "Риск" },
 ]}
 />
 </div>

 <label className="flex items-start gap-2.5 sm:col-span-2">
 <input
 type="checkbox"
 className="mt-1 h-4 w-4 accent-[hsl(var(--primary))]"
 checked={prefs.notify_email}
 onChange={(e) =>
 setPrefs({ ...prefs, notify_email: e.target.checked })
 }
 />
 <span className="type-subhead">
 Изпращайте ми известията и по имейл
 {!emailEnabled && (
 <span className="block type-caption text-muted-foreground">
 Изпращането още не е конфигурирано на сървъра — известията се
 виждат тук, в приложението.
 </span>
 )}
 </span>
 </label>

 <div className="flex items-center gap-3 sm:col-span-2">
 <Button type="submit" disabled={busy}>
 {busy ? "Запазвам..." : "Запази"}
 </Button>
 </div>
 </form>
 </CardContent>
 </Card>
 );
}

export default function AlertsPage() {
 const router = useRouter();
 const [feed, setFeed] = useState<NotificationFeed | null>(null);
 const [loading, setLoading] = useState(true);
 const [checking, setChecking] = useState(false);
 const [error, setError] = useState<string | null>(null);

 const load = useCallback(() => {
 api
 .notifications()
 .then(setFeed)
 .catch((e: Error) => setError(e.message))
 .finally(() => setLoading(false));
 }, []);

 useEffect(() => {
 if (getToken() === null) {
 router.push("/login");
 return;
 }
 load();
 }, [load, router]);

 async function checkNow() {
 setChecking(true);
 try {
 setFeed(await api.checkNow());
 } catch (e) {
 setError((e as Error).message);
 } finally {
 setChecking(false);
 }
 }

 async function readAll() {
 setFeed(await api.markAllRead());
 }

 if (loading) return <Skeleton className="h-64 w-full" />;

 return (
 <div className="cascade space-y-6">
 <div className="flex flex-wrap items-start justify-between gap-3">
 <div>
 <h1 className="type-title-1">Известия</h1>
 <p className="mt-1 max-w-prose type-subhead text-muted-foreground">
 Приложението проверява кредитите ви всяка вечер и се обажда само
 когато има какво конкретно да ви каже.
 </p>
 </div>
 <div className="flex gap-2">
 <Button variant="outline" size="sm" onClick={checkNow} disabled={checking}>
 <RefreshCw
 className={cn("h-4 w-4", checking && "animate-spin")}
 aria-hidden
 />
 {checking ? "Проверявам..." : "Провери сега"}
 </Button>
 {(feed?.unread_count ?? 0) > 0 && (
 <Button variant="ghost" size="sm" onClick={readAll}>
 Отбележи всички
 </Button>
 )}
 </div>
 </div>

 {error && <Alert tone="bad">{error}</Alert>}

 {feed && feed.items.length === 0 && (
 <Alert>
 Няма известия. Това е добра новина — значи нищо във вашите кредити не
 се е променило над прага, който сте задали.
 </Alert>
 )}

 <div className="space-y-3">
 {feed?.items.map((item) => {
 const severity = SEVERITY[item.severity];
 const unread = item.read_at === null;
 return (
 <Card
 key={item.id}
 className={cn(
 "border-l-4 transition-opacity",
 severity.ring,
 !unread && "opacity-70",
 )}
 >
 <CardContent className="pt-5">
 <div className="flex flex-wrap items-start justify-between gap-2">
 <div className="flex items-center gap-2">
 {unread && (
 <BellRing className="h-4 w-4 text-primary" aria-hidden />
 )}
 <h2 className="type-body font-semibold">{item.title_bg}</h2>
 </div>
 <div className="flex shrink-0 items-center gap-2">
 <Badge tone={severity.tone}>{severity.label}</Badge>
 <span className="type-caption text-muted-foreground">
 {relativeTime(item.created_at)}
 </span>
 </div>
 </div>

 <p className="mt-2 type-subhead leading-relaxed text-muted-foreground">
 {item.body_bg}
 </p>

 {item.action_bg && (
 <p className="mt-3 rounded-xl bg-accent px-3 py-2 type-subhead font-medium">
 {item.action_bg}
 </p>
 )}

 {unread && (
 <button
 type="button"
 onClick={async () => {
 await api.markRead(item.id);
 load();
 }}
 className="mt-3 type-caption font-medium text-primary hover:underline"
 >
 Отбележи като прочетено
 </button>
 )}
 </CardContent>
 </Card>
 );
 })}
 </div>

 <PreferencesPanel
 emailEnabled={feed?.email_delivery_enabled ?? false}
 onSaved={load}
 />
 </div>
 );
}
