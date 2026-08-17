"use client";

import { useEffect, useState } from "react";

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
import { OfferCheck } from "@/components/offer-check";
import { PartnerCard } from "@/components/partner-card";
import {
 api,
 type CalculatorResult,
 type CompareResult,
 type Currency,
 type LoanType,
} from "@/lib/api";
import { money, percent } from "@/lib/utils";

export default function CalculatorPage() {
 const [amount, setAmount] = useState(200000);
 const [months, setMonths] = useState(300);
 const [rate, setRate] = useState(4.2);
 const [monthlyFee, setMonthlyFee] = useState(0);
 const [upfrontFee, setUpfrontFee] = useState(0);
 const [currency, setCurrency] = useState<Currency>("EUR");
 const [loanType, setLoanType] = useState<LoanType>("MORTGAGE");
 const [propertyValue, setPropertyValue] = useState<number | "">("");
 const [sortBy, setSortBy] = useState<"apr" | "monthly_payment" | "total_cost">(
 "apr",
 );

 const [result, setResult] = useState<CalculatorResult | null>(null);
 const [comparison, setComparison] = useState<CompareResult | null>(null);
 const [error, setError] = useState<string | null>(null);
 const [busy, setBusy] = useState(false);
 const [showSchedule, setShowSchedule] = useState(false);

 async function run() {
 setBusy(true);
 setError(null);
 try {
 const [calculation, banks] = await Promise.all([
 api.calculate({
 amount,
 months,
 annual_rate_pct: rate,
 monthly_fee: monthlyFee,
 upfront_fee: upfrontFee,
 }),
 api.compareBanks({
 amount,
 months,
 loan_type: loanType,
 currency,
 property_value: propertyValue === "" ? null : propertyValue,
 sort_by: sortBy,
 }),
 ]);
 setResult(calculation);
 setComparison(banks);
 } catch (err) {
 setError((err as Error).message);
 } finally {
 setBusy(false);
 }
 }

 useEffect(() => {
 run();
 // Първоначално зареждане с подразбиращите се стойности.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 }, []);

 return (
 <div className="space-y-4">
 <div>
 <h1 className="type-title-1">Калкулатор за кредит</h1>
 <p className="mt-1 max-w-prose type-subhead text-muted-foreground">
 Започнете с проверка на офертата, която вече ви предлагат. Пълният
 калкулатор е под нея.
 </p>
 </div>

 <OfferCheck />

 <Card>
 <CardHeader>
 <CardTitle>Параметри на кредита</CardTitle>
 <CardDescription>
 Вноската се смята по ануитетна формула, а ГПР — по метода от Закона
 за потребителския кредит.
 </CardDescription>
 </CardHeader>
 <CardContent>
 <form
 onSubmit={(e) => {
 e.preventDefault();
 run();
 }}
 className="grid gap-4 sm:grid-cols-3"
 >
 <div>
 <Label htmlFor="amount">Сума на кредита</Label>
 <Input
 id="amount"
 type="number"
 min={1}
 step="any"
 value={amount}
 onChange={(e) => setAmount(Number(e.target.value))}
 />
 </div>
 <div>
 <Label htmlFor="months">Срок (месеци)</Label>
 <Input
 id="months"
 type="number"
 min={6}
 max={480}
 value={months}
 onChange={(e) => setMonths(Number(e.target.value))}
 />
 </div>
 <div>
 <Label htmlFor="rate">Годишна лихва (%)</Label>
 <Input
 id="rate"
 type="number"
 min={0}
 step={0.01}
 value={rate}
 onChange={(e) => setRate(Number(e.target.value))}
 />
 </div>
 <div>
 <Label htmlFor="monthlyFee">Месечна такса</Label>
 <Input
 id="monthlyFee"
 type="number"
 min={0}
 step="any"
 value={monthlyFee}
 onChange={(e) => setMonthlyFee(Number(e.target.value))}
 />
 </div>
 <div>
 <Label htmlFor="upfront">Първоначални такси</Label>
 <Input
 id="upfront"
 type="number"
 min={0}
 step="any"
 value={upfrontFee}
 onChange={(e) => setUpfrontFee(Number(e.target.value))}
 />
 </div>
 <div>
 <Label htmlFor="currency">Валута</Label>
 <Select
 id="currency"
 value={currency}
 onChange={(e) => setCurrency(e.target.value as Currency)}
 >
 <option value="EUR">Евро (EUR)</option>
 <option value="BGN">Лева (BGN)</option>
 </Select>
 </div>
 <div>
 <Label htmlFor="loanType">Вид кредит</Label>
 <Select
 id="loanType"
 value={loanType}
 onChange={(e) => setLoanType(e.target.value as LoanType)}
 >
 <option value="MORTGAGE">Ипотечен</option>
 <option value="CONSUMER">Потребителски</option>
 </Select>
 </div>
 <div>
 <Label htmlFor="property">Стойност на имота (по избор)</Label>
 <Input
 id="property"
 type="number"
 min={0}
 step="any"
 value={propertyValue}
 onChange={(e) =>
 setPropertyValue(
 e.target.value === "" ? "" : Number(e.target.value),
 )
 }
 />
 </div>
 <div>
 <Label htmlFor="sort">Подреждане на офертите</Label>
 <Select
 id="sort"
 value={sortBy}
 onChange={(e) =>
 setSortBy(e.target.value as typeof sortBy)
 }
 >
 <option value="apr">По ГПР</option>
 <option value="monthly_payment">По месечна вноска</option>
 <option value="total_cost">По обща цена</option>
 </Select>
 </div>

 <div className="sm:col-span-3">
 <Button type="submit" disabled={busy}>
 {busy ? "Смятам..." : "Изчисли"}
 </Button>
 </div>
 </form>
 </CardContent>
 </Card>

 {error && <Alert tone="bad">{error}</Alert>}

 <PartnerCard />

 {result && (
 <Card>
 <CardHeader>
 <CardTitle>Вашата вноска</CardTitle>
 </CardHeader>
 <CardContent>
 <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
 <div>
 <div className="type-caption text-muted-foreground">
 Месечна вноска
 </div>
 <div className="mt-1 type-title-1 tabular-nums">
 {money(result.monthly_payment, currency)}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">ГПР</div>
 <div className="mt-1 type-title-1 tabular-nums">
 {percent(result.apr_pct)}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">Общо лихва</div>
 <div className="mt-1 type-title-1 tabular-nums">
 {money(result.total_interest, currency)}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 Общо ще платите
 </div>
 <div className="mt-1 type-title-1 tabular-nums">
 {money(result.total_paid, currency)}
 </div>
 </div>
 </div>

 <button
 type="button"
 onClick={() => setShowSchedule((v) => !v)}
 className="mt-4 type-subhead font-medium text-primary hover:underline"
 >
 {showSchedule ? "Скрий" : "Покажи"} погасителния план (
 {result.schedule.length} месеца)
 </button>

 {showSchedule && (
 <div className="mt-3 max-h-80 overflow-auto rounded-xl border border-border">
 <table className="w-full type-subhead">
 <thead className="sticky top-0 bg-muted type-caption">
 <tr>
 <th className="px-3 py-2 text-left">Месец</th>
 <th className="px-3 py-2 text-right">Вноска</th>
 <th className="px-3 py-2 text-right">Лихва</th>
 <th className="px-3 py-2 text-right">Главница</th>
 <th className="px-3 py-2 text-right">Остатък</th>
 </tr>
 </thead>
 <tbody>
 {result.schedule.map((row) => (
 <tr key={row.month} className="border-t border-border">
 <td className="px-3 py-1.5">{row.month}</td>
 <td className="px-3 py-1.5 text-right tabular-nums">
 {row.payment.toFixed(2)}
 </td>
 <td className="px-3 py-1.5 text-right tabular-nums text-bad">
 {row.interest.toFixed(2)}
 </td>
 <td className="px-3 py-1.5 text-right tabular-nums text-good">
 {row.principal.toFixed(2)}
 </td>
 <td className="px-3 py-1.5 text-right tabular-nums">
 {row.balance.toFixed(2)}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )}
 </CardContent>
 </Card>
 )}

 {comparison && (
 <Card>
 <CardHeader>
 <CardTitle>Сравнение на банкови оферти</CardTitle>
 <CardDescription>
 {comparison.market_average_note_bg}
 </CardDescription>
 </CardHeader>
 <CardContent>
 {comparison.quotes.length === 0 ? (
 <Alert>
 В базата все още няма заредени банкови тарифи. Приложението
 съзнателно не показва измислени лихви — числата, по които хората
 избират кредит, трябва да идват от публикуваната тарифа на
 банката.
 </Alert>
 ) : (
 <div className="overflow-x-auto">
 <table className="w-full min-w-[720px] type-subhead">
 <thead className="bg-muted type-caption">
 <tr>
 <th className="px-3 py-2 text-left">Банка</th>
 <th className="px-3 py-2 text-right">Лихва</th>
 <th className="px-3 py-2 text-right">Вноска</th>
 <th className="px-3 py-2 text-right">Общо месечно</th>
 <th className="px-3 py-2 text-right">ГПР</th>
 <th className="px-3 py-2 text-right">Обща цена</th>
 <th className="px-3 py-2 text-left">Тарифа</th>
 </tr>
 </thead>
 <tbody>
 {comparison.quotes.map((quote) => (
 <tr
 key={`${quote.bank_name}-${quote.product_name}`}
 className={
 quote.disqualified_reason
 ? "border-t border-border opacity-50"
 : "border-t border-border"
 }
 >
 <td className="px-3 py-2">
 <div className="font-medium">{quote.bank_name}</div>
 <div className="type-caption text-muted-foreground">
 {quote.product_name}
 </div>
 {quote.disqualified_reason && (
 <div className="type-caption text-bad">
 {quote.disqualified_reason}
 </div>
 )}
 </td>
 <td className="px-3 py-2 text-right tabular-nums">
 {percent(quote.nominal_rate_pct)}
 </td>
 <td className="px-3 py-2 text-right tabular-nums">
 {quote.monthly_payment.toFixed(2)}
 </td>
 <td className="px-3 py-2 text-right tabular-nums">
 {quote.total_monthly_cost.toFixed(2)}
 </td>
 <td className="px-3 py-2 text-right font-semibold tabular-nums">
 {percent(quote.apr_pct)}
 </td>
 <td className="px-3 py-2 text-right tabular-nums">
 {quote.total_cost.toFixed(0)}
 </td>
 <td className="px-3 py-2">
 <a
 href={quote.source_url}
 target="_blank"
 rel="noopener noreferrer"
 className="type-caption text-primary hover:underline"
 >
 {quote.rate_effective_date}
 </a>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )}

 <div className="mt-4 grid gap-2 type-caption text-muted-foreground sm:grid-cols-3">
 {Object.entries(comparison.index_values).map(([code, value]) => (
 <div key={code}>
 {code}: <strong>{percent(value)}</strong>
 </div>
 ))}
 {comparison.inflation_bg_pct !== null && (
 <div>
 Инфлация БГ:{" "}
 <strong>{percent(comparison.inflation_bg_pct)}</strong>
 </div>
 )}
 </div>
 </CardContent>
 </Card>
 )}
 </div>
 );
}
