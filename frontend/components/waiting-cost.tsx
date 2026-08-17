"use client";

import { useCallback, useEffect, useState } from "react";

import {
 Button,
 Input,
 Label,
} from "@/components/ui";
import { api, type Waiting } from "@/lib/api";
import { cn, money, percent } from "@/lib/utils";

export function WaitingCost() {
 const [price, setPrice] = useState(200000);
 const [downPct, setDownPct] = useState(20);
 const [saved, setSaved] = useState(15000);
 const [monthly, setMonthly] = useState(800);
 const [growth, setGrowth] = useState<number | "">("");
 const [result, setResult] = useState<Waiting | null>(null);
 const [busy, setBusy] = useState(false);

 const run = useCallback(() => {
 setBusy(true);
 api
 .costOfWaiting({
 target_price: price,
 down_payment_pct: downPct,
 saved_now: saved,
 monthly_saving: monthly,
 house_growth_pct: growth === "" ? null : growth,
 })
 .then(setResult)
 .catch(() => setResult(null))
 .finally(() => setBusy(false));
 }, [price, downPct, saved, monthly, growth]);

 useEffect(() => {
 run();
 // eslint-disable-next-line react-hooks/exhaustive-deps
 }, []);

 return (
    <>
 <form
 onSubmit={(e) => {
 e.preventDefault();
 run();
 }}
 className="grid gap-3 sm:grid-cols-3"
 >
 <div>
 <Label htmlFor="w-price">Цена на жилището</Label>
 <Input id="w-price" type="number" min={1} step="any" value={price}
 onChange={(e) => setPrice(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="w-down">Самоучастие (%)</Label>
 <Input id="w-down" type="number" min={0} max={100} step="any" value={downPct}
 onChange={(e) => setDownPct(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="w-saved">Спестени сега</Label>
 <Input id="w-saved" type="number" min={0} step="any" value={saved}
 onChange={(e) => setSaved(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="w-monthly">Спестявам месечно</Label>
 <Input id="w-monthly" type="number" min={0} step="any" value={monthly}
 onChange={(e) => setMonthly(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="w-growth">Ръст на цените (%)</Label>
 <Input id="w-growth" type="number" step="any" value={growth}
 placeholder={result ? String(result.house_growth_pct) : "по данни"}
 onChange={(e) =>
 setGrowth(e.target.value === "" ? "" : Number(e.target.value))
 } />
 </div>
 <div className="flex items-end">
 <Button type="submit" className="w-full" disabled={busy}>
 {busy ? "Смятам..." : "Изчисли"}
 </Button>
 </div>
 </form>

 {result && (
 <div className="mt-5">
 <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
 <div>
 <div className="type-caption text-muted-foreground">Нужно сега</div>
 <div className="mt-1 type-title-2 tabular-nums">
 {money(result.needed_now, "EUR")}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">След година</div>
 <div className="mt-1 type-title-2 tabular-nums">
 {money(result.needed_in_year, "EUR")}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 Чакането струва
 </div>
 <div className="mt-1 type-title-2 tabular-nums text-bad">
 +{money(result.cost_of_one_year, "EUR")}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 Събирате го за
 </div>
 <div
 className={cn(
 "mt-1 type-title-2 tabular-nums",
 result.gap_is_widening && "text-bad",
 )}
 >
 {result.months_to_afford === null
 ? "не се събира"
 : result.months_to_afford === 0
 ? "вече имате"
 : `${result.months_to_afford} мес.`}
 </div>
 </div>
 </div>

 <div
 className={cn(
 "mt-4 rounded-xl p-3 type-subhead leading-relaxed",
 result.gap_is_widening
 ? "bg-bad/10 text-bad"
 : "bg-muted text-muted-foreground",
 )}
 >
 {result.verdict_bg}
 </div>

 <p className="mt-3 type-caption leading-relaxed text-muted-foreground">
 Ръст {percent(result.house_growth_pct, 1)}{" "}
 {result.house_growth_is_observed
 ? `(отчетен от Евростат за ${result.house_growth_period})`
 : "(въведен от вас)"}
 , доходност на спестяванията{" "}
 {percent(result.deposit_rate_pct)}. {result.assumption_note_bg}
 </p>
 </div>
 )}
    </>
 );
}
