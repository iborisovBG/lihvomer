"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";

import { Disclosure } from "@/components/ios";
import { PartnerCard } from "@/components/partner-card";
import { WaitingCost } from "@/components/waiting-cost";
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
 Select,
 Skeleton,
} from "@/components/ui";
import { api, getToken, type LoanHealth, type Savings } from "@/lib/api";
import { LargeTitle } from "@/components/large-title";
import { cn, money, percent } from "@/lib/utils";

function SavingsPanel() {
 const [amount, setAmount] = useState(20000);
 const [kind, setKind] = useState<"term" | "current">("current");
 const [result, setResult] = useState<Savings | null>(null);
 const [busy, setBusy] = useState(false);

 const run = useCallback(() => {
 setBusy(true);
 api
 .savings(amount, kind === "term")
 .then(setResult)
 .catch(() => setResult(null))
 .finally(() => setBusy(false));
 }, [amount, kind]);

 useEffect(() => {
 run();
 // eslint-disable-next-line react-hooks/exhaustive-deps
 }, []);

 const losing = result !== null && result.real_rate_pct < 0;

 return (
    <>
 <form
 onSubmit={(e) => {
 e.preventDefault();
 run();
 }}
 className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end"
 >
 <div>
 <Label htmlFor="savings-amount">Спестявания</Label>
 <Input
 id="savings-amount"
 type="number"
 min={1}
 step="any"
 value={amount}
 onChange={(e) => setAmount(Number(e.target.value))}
 />
 </div>
 <div>
 <Label htmlFor="savings-kind">Къде ги държите</Label>
 <Select
 id="savings-kind"
 value={kind}
 onChange={(e) => setKind(e.target.value as "term" | "current")}
 >
 <option value="current">Разплащателна сметка</option>
 <option value="term">Срочен депозит</option>
 </Select>
 </div>
 <Button type="submit" disabled={busy}>
 {busy ? "Смятам..." : "Изчисли"}
 </Button>
 </form>

 {result && (
 <div className="mt-5">
 <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
 <div>
 <div className="type-caption text-muted-foreground">
 Лихва ({result.deposit_kind_bg})
 </div>
 <div className="mt-1 type-title-2 tabular-nums">
 {percent(result.deposit_rate_pct)}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">Инфлация</div>
 <div className="mt-1 type-title-2 tabular-nums">
 {percent(result.inflation_pct)}
 </div>
 <div className="type-caption text-muted-foreground">
 към {result.inflation_period}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 Реална доходност
 </div>
 <div
 className={cn(
 "mt-1 type-title-2 tabular-nums",
 losing && "text-bad",
 )}
 >
 {percent(result.real_rate_pct)}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 Загуба за 5 години
 </div>
 <div
 className={cn(
 "mt-1 type-title-2 tabular-nums",
 losing && "text-bad",
 )}
 >
 {money(Math.abs(result.five_year_loss), "EUR")}
 </div>
 </div>
 </div>

 <div
 className={cn(
 "mt-4 rounded-xl p-3 type-subhead leading-relaxed",
 losing
 ? "bg-bad/10 text-bad"
 : "bg-good/10 text-good",
 )}
 >
 {result.verdict_bg}
 </div>
 </div>
 )}
    </>
 );
}

function LoanHealthCard({ health }: { health: LoanHealth }) {
 const { market, refinance, currency } = health;

 return (
 <Card>
 <CardHeader>
 <div className="flex flex-wrap items-start justify-between gap-2">
 <div>
 <CardTitle>{health.label}</CardTitle>
 <CardDescription>
 {health.bank_name} · {money(health.principal_amount, currency)} ·{" "}
 {health.remaining_months} месеца
 </CardDescription>
 </div>
 <Badge tone={market.is_above_market ? "bad" : "good"}>
 {market.is_above_market ? "Над пазара" : "Добра лихва"}
 </Badge>
 </div>
 </CardHeader>
 <CardContent className="space-y-5">
 <section>
 <div className="mb-2 flex items-center gap-2">
 {market.is_above_market ? (
 <TrendingUp className="h-4 w-4 text-bad" aria-hidden />
 ) : (
 <TrendingDown className="h-4 w-4 text-good" aria-hidden />
 )}
 <h3 className="type-subhead font-semibold">Плащам ли повече от пазара?</h3>
 </div>

 <div className="grid grid-cols-3 gap-3">
 <div className="rounded-xl bg-muted p-3">
 <div className="type-caption text-muted-foreground">Вашата лихва</div>
 <div className="mt-0.5 type-title-3 tabular-nums">
 {percent(market.your_rate_pct)}
 </div>
 </div>
 <div className="rounded-xl bg-muted p-3">
 <div className="type-caption text-muted-foreground">
 Средна за нови
 </div>
 <div className="mt-0.5 type-title-3 tabular-nums">
 {percent(market.market_rate_pct)}
 </div>
 <div className="type-caption text-muted-foreground">
 {market.market_period}
 </div>
 </div>
 <div className="rounded-xl bg-muted p-3">
 <div className="type-caption text-muted-foreground">Разлика</div>
 <div
 className={cn(
 "mt-0.5 type-title-3 tabular-nums",
 market.is_above_market
 ? "text-bad"
 : "text-good",
 )}
 >
 {market.difference_pp > 0 ? "+" : ""}
 {market.difference_pp.toFixed(2).replace(".", ",")} п.
 </div>
 </div>
 </div>

 <p className="mt-3 type-subhead leading-relaxed text-muted-foreground">
 {market.verdict_bg}
 </p>
 </section>

 <section className="border-t border-border pt-4">
 <h3 className="mb-2 type-subhead font-semibold">
 Струва ли си рефинансирането?
 </h3>
 <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
 <div>
 <div className="type-caption text-muted-foreground">Сега</div>
 <div className="mt-0.5 font-bold tabular-nums">
 {money(health.current_monthly_payment, currency)}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 При пазарна лихва
 </div>
 <div className="mt-0.5 font-bold tabular-nums">
 {money(refinance.new_monthly_payment, currency)}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 Такси се покриват
 </div>
 <div className="mt-0.5 font-bold tabular-nums">
 {refinance.break_even_month === null
 ? "не се покриват"
 : refinance.break_even_month === 0
 ? "няма такси"
 : `${refinance.break_even_month} мес.`}
 </div>
 </div>
 <div>
 <div className="type-caption text-muted-foreground">
 Полза до края
 </div>
 <div
 className={cn(
 "mt-0.5 font-bold tabular-nums",
 refinance.is_worth_it &&
 "text-good",
 )}
 >
 {money(refinance.total_saving_over_term, currency)}
 </div>
 </div>
 </div>
 <p className="mt-3 type-subhead leading-relaxed text-muted-foreground">
 {refinance.verdict_bg}
 </p>
 </section>

 <section className="border-t border-border pt-4">
 <h3 className="mb-2 type-subhead font-semibold">
 Ако плащам малко повече всеки месец
 </h3>
 <div className="overflow-x-auto">
 <table className="w-full min-w-[420px] type-subhead">
 <thead>
 <tr className="type-caption text-muted-foreground">
 <th className="pb-2 text-left font-medium">Допълнително</th>
 <th className="pb-2 text-right font-medium">
 Изплащате по-рано
 </th>
 <th className="pb-2 text-right font-medium">
 Спестена лихва
 </th>
 </tr>
 </thead>
 <tbody>
 {health.early_repayment.map((option) => (
 <tr
 key={option.extra_monthly}
 className="border-t border-border/60"
 >
 <td className="py-2 tabular-nums">
 +{money(option.extra_monthly, currency)}
 </td>
 <td className="py-2 text-right tabular-nums">
 {option.months_saved > 0
 ? `${option.months_saved} месеца`
 : "—"}
 </td>
 <td className="py-2 text-right font-medium tabular-nums text-good">
 {option.interest_saved > 1
 ? money(option.interest_saved, currency)
 : "—"}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 <p className="mt-2 type-caption text-muted-foreground">
 По закон таксата за предсрочно погасяване при жилищните кредити
 отпада след първите 12 месеца от усвояването.
 </p>
 </section>
 </CardContent>
 </Card>
 );
}

/** Едно изречение, което казва къде стои потребителят спрямо пазара. */
function Verdict({ items }: { items: LoanHealth[] }) {
  const above = items.filter((h) => h.market.is_above_market);
  if (items.length === 0) return null;

  const overpayMonthly = above.reduce(
    (sum, h) => sum + Math.abs(h.market.monthly_difference),
    0,
  );
  const overpayTotal = above.reduce(
    (sum, h) => sum + Math.abs(h.market.remaining_term_difference),
    0,
  );

  const currency = items[0].currency;

  return (
    <section
      aria-labelledby="verdict"
      className="glass glass-specular rounded-[1.5rem] bg-gradient-to-br from-accent/70 to-surface/30 p-6 md:p-8"
    >
      <p className="type-subhead font-medium text-label-secondary">
        {above.length > 0 ? "Плащате над пазара" : "Стоите добре спрямо пазара"}
      </p>
      <p
        id="verdict"
        className={cn(
          "mt-2 type-large-title tabular-nums",
          above.length > 0 ? "text-bad" : "text-good",
        )}
      >
        {above.length > 0 ? (
          <>
            {money(overpayMonthly, currency)}
            <span className="ml-2 type-title-3 font-normal text-label-secondary">
              на месец повече
            </span>
          </>
        ) : (
          "Няма преплащане"
        )}
      </p>
      <p className="mt-3 max-w-xl type-body text-label-secondary">
        {above.length > 0
          ? `До края на срока разликата е ${money(overpayTotal, currency)}. Струва си да поискате предоговаряне — банките рядко го предлагат сами.`
          : "Лихвите по кредитите ви са на нивото на средните за нови кредити или под тях. Предоговаряне най-вероятно не би подобрило условията."}
      </p>
    </section>
  );
}

export default function HealthPage() {
 const router = useRouter();
 const [items, setItems] = useState<LoanHealth[]>([]);
 const [refinanceCost, setRefinanceCost] = useState(0);
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState<string | null>(null);

 const load = useCallback((cost: number) => {
 api
 .loanHealth(cost)
 .then(setItems)
 .catch((e: Error) => setError(e.message))
 .finally(() => setLoading(false));
 }, []);

 useEffect(() => {
 if (getToken() === null) {
 router.push("/login");
 return;
 }
 load(0);
 }, [load, router]);

 return (
 <div className="cascade space-y-6">
 <LargeTitle
        title="Аз добре ли съм?"
        description="Сравняваме вашия кредит със средното за пазара по данни на ЕЦБ и показваме какво бихте спестили при различни решения. Всички суми са изчислени, не приблизителни."
      />

 {error && <Alert tone="bad">{error}</Alert>}
 {loading && <Skeleton className="h-64 w-full" />}

 {items.length > 0 && <Verdict items={items} />}

      {!loading && items.length === 0 && !error && (
 <Alert>
 Нямате въведени кредити. Добавете кредит в раздел „Кредити“, за да
 видите как стоите спрямо пазара.
 </Alert>
 )}

 {items.length > 0 && (
 <Card>
 <CardContent className="pt-5">
 <form
 onSubmit={(e) => {
 e.preventDefault();
 load(refinanceCost);
 }}
 className="flex flex-wrap items-end gap-3"
 >
 <div className="min-w-[12rem] flex-1">
 <Label htmlFor="cost">
 Разходи по рефинансиране (по ваша преценка)
 </Label>
 <Input
 id="cost"
 type="number"
 min={0}
 step="any"
 value={refinanceCost}
 onChange={(e) => setRefinanceCost(Number(e.target.value))}
 />
 </div>
 <Button type="submit">Преизчисли</Button>
 </form>
 <p className="mt-2 type-caption leading-relaxed text-muted-foreground">
 {items[0].refinance_cost_note_bg}
 </p>
 </CardContent>
 </Card>
 )}

 {items.map((health) => (
 <LoanHealthCard key={health.loan_id} health={health} />
 ))}

      <div className="space-y-3">
        <h2 className="px-1 type-caption font-semibold uppercase tracking-wider text-muted-foreground">
          Инструменти
        </h2>
        <Disclosure
          title="Колко губят спестяванията ми"
          summary="Ако лихвата по депозита е под инфлацията, парите губят стойност."
        >
          <SavingsPanel />
        </Disclosure>
        <Disclosure
          title="Колко ми струва да чакам"
          summary="Цените на жилищата и спестяванията растат с различна скорост."
        >
          <WaitingCost />
        </Disclosure>
      </div>

 {items.length > 0 && <PartnerCard />}
 </div>
 );
}
