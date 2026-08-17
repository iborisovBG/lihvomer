"use client";

import { useCallback, useEffect, useState } from "react";
import { ScanSearch } from "lucide-react";

import {
 Alert,
 Button,
 Card,
 CardContent,
 CardDescription,
 CardHeader,
 CardTitle,
 Input,
 Label,
 Select,
} from "@/components/ui";
import { api, type LoanType, type OfferVerdict } from "@/lib/api";
import { cn, money, percent } from "@/lib/utils";

/**
 * Обръща посоката на сравнението: вместо класация на банки — за която няма
 * публичен източник — измерва офертата на потребителя срещу пазарния ГПР,
 * който идва автоматично от ЕЦБ.
 */
export function OfferCheck() {
 const [amount, setAmount] = useState(200000);
 const [months, setMonths] = useState(300);
 const [loanType, setLoanType] = useState<LoanType>("MORTGAGE");
 const [rate, setRate] = useState(2.5);
 const [monthlyFee, setMonthlyFee] = useState(15);
 const [upfront, setUpfront] = useState(2000);
 const [propertyIns, setPropertyIns] = useState(0.1);
 const [lifeIns, setLifeIns] = useState(0.3);
 const [result, setResult] = useState<OfferVerdict | null>(null);
 const [error, setError] = useState<string | null>(null);
 const [busy, setBusy] = useState(false);

 const run = useCallback(() => {
 setBusy(true);
 setError(null);
 api
 .evaluateOffer({
 amount,
 months,
 loan_type: loanType,
 nominal_rate_pct: rate,
 monthly_fee: monthlyFee,
 upfront_fee: upfront,
 property_insurance_annual_pct: propertyIns,
 life_insurance_annual_pct: lifeIns,
 })
 .then(setResult)
 .catch((e: Error) => setError(e.message))
 .finally(() => setBusy(false));
 }, [amount, months, loanType, rate, monthlyFee, upfront, propertyIns, lifeIns]);

 useEffect(() => {
 run();
 // eslint-disable-next-line react-hooks/exhaustive-deps
 }, []);

 const worse = result?.is_above_market ?? false;
 const better = result !== null && result.difference_pp < -0.15;

 return (
 <Card>
 <CardHeader>
 <div className="flex items-center gap-2">
 <ScanSearch className="h-5 w-5 text-primary" aria-hidden />
 <CardTitle>Добра ли е офертата, която ми предлагат?</CardTitle>
 </div>
 <CardDescription>
 Въведете какво ви предлага банката. Сравняваме по ГПР срещу средния за
 пазара от ЕЦБ — обявената лихва подвежда, защото не включва таксите.
 </CardDescription>
 </CardHeader>
 <CardContent>
 <form
 onSubmit={(e) => {
 e.preventDefault();
 run();
 }}
 className="grid gap-3 sm:grid-cols-4"
 >
 <div>
 <Label htmlFor="o-amount">Сума</Label>
 <Input id="o-amount" type="number" min={1} step="any" value={amount}
 onChange={(e) => setAmount(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="o-months">Срок (месеци)</Label>
 <Input id="o-months" type="number" min={6} max={480} value={months}
 onChange={(e) => setMonths(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="o-type">Вид</Label>
 <Select id="o-type" value={loanType}
 onChange={(e) => setLoanType(e.target.value as LoanType)}>
 <option value="MORTGAGE">Ипотечен</option>
 <option value="CONSUMER">Потребителски</option>
 </Select>
 </div>
 <div>
 <Label htmlFor="o-rate">Обявена лихва (%)</Label>
 <Input id="o-rate" type="number" min={0} step="any" value={rate}
 onChange={(e) => setRate(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="o-fee">Месечна такса</Label>
 <Input id="o-fee" type="number" min={0} step="any" value={monthlyFee}
 onChange={(e) => setMonthlyFee(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="o-up">Такси при отпускане</Label>
 <Input id="o-up" type="number" min={0} step="any" value={upfront}
 onChange={(e) => setUpfront(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="o-pi">Имуществена застр. (%/г.)</Label>
 <Input id="o-pi" type="number" min={0} step="any" value={propertyIns}
 onChange={(e) => setPropertyIns(Number(e.target.value))} />
 </div>
 <div>
 <Label htmlFor="o-li">Живот застр. (%/г.)</Label>
 <Input id="o-li" type="number" min={0} step="any" value={lifeIns}
 onChange={(e) => setLifeIns(Number(e.target.value))} />
 </div>
 <div className="sm:col-span-4">
 <Button type="submit" disabled={busy}>
 {busy ? "Проверявам..." : "Провери офертата"}
 </Button>
 </div>
 </form>

 {error && (
 <div className="mt-4">
 <Alert tone="bad">{error}</Alert>
 </div>
 )}

 {result && (
 <div className="mt-6">
 <div
 className={cn(
 "rounded-2xl p-5",
 worse
 ? "bg-bad/10"
 : better
 ? "bg-good/10"
 : "bg-muted",
 )}
 >
 <p className="type-subhead font-medium text-muted-foreground">
 Реален ГПР на офертата
 </p>
 <p
 className={cn(
 "mt-1 type-large-title tabular-nums md:type-large-title",
 worse && "text-bad",
 better && "text-good",
 )}
 >
 {percent(result.offer_aprc_pct)}
 </p>
 <p className="mt-2 type-subhead text-muted-foreground">
 срещу {percent(result.market_aprc_pct)} среден за пазара (
 {result.market_period})
 </p>
 </div>

 <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
 <div>
 <div className="type-caption text-muted-foreground">Вноска</div>
 <div className="mt-1 font-bold tabular-nums">
 {money(result.monthly_payment, "EUR")}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 С такси и застраховки
 </div>
 <div className="mt-1 font-bold tabular-nums">
 {money(result.total_monthly_cost, "EUR")}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 Спрямо пазара
 </div>
 <div
 className={cn(
 "mt-1 font-bold tabular-nums",
 worse && "text-bad",
 better && "text-good",
 )}
 >
 {result.difference_pp > 0 ? "+" : ""}
 {result.difference_pp.toFixed(2).replace(".", ",")} п.
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 За целия срок
 </div>
 <div
 className={cn(
 "mt-1 font-bold tabular-nums",
 worse && "text-bad",
 )}
 >
 {result.total_difference > 0 ? "+" : ""}
 {money(result.total_difference, "EUR")}
 </div>
 </div>
 </div>

 <p className="mt-4 type-subhead leading-relaxed text-muted-foreground">
 {result.verdict_bg}
 </p>

 {result.hidden_cost_pp > 0.05 && (
 <p
 className={cn(
 "mt-3 rounded-xl p-3 type-subhead leading-relaxed",
 result.hidden_cost_pp > 0.5
 ? "bg-warn/10 text-warn"
 : "bg-muted text-muted-foreground",
 )}
 >
 {result.hidden_cost_note_bg}
 </p>
 )}
 </div>
 )}
 </CardContent>
 </Card>
 );
}
