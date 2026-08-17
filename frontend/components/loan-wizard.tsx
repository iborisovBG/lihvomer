"use client";

import { useMemo, useState } from "react";
import { ArrowLeft, Check } from "lucide-react";

import { Alert, Button, Input, Label } from "@/components/ui";
import { Segmented, useToast } from "@/components/ios";
import { api, type Loan, type LoanInput, type LoanType } from "@/lib/api";
import { cn, money } from "@/lib/utils";

/**
 * Въвеждане на кредит като разговор, не като формуляр.
 *
 * Десет полета на един екран отблъскват — човекът не знае откъде да започне и
 * не вижда защо му трябват. Тук всяка стъпка задава един въпрос и показва
 * какво се е получило дотук, за да е ясно, че въвеждането води донякъде.
 */

const BANKS = [
  "Банка ДСК",
  "УниКредит Булбанк",
  "Обединена българска банка (ОББ)",
  "Пощенска банка",
  "Първа инвестиционна банка (Fibank)",
  "Централна кооперативна банка",
  "Алианц Банк България",
  "Инвестбанк",
  "Общинска банка",
  "Друга",
];

const RATE_KINDS = [
  {
    value: "EURIBOR_3M",
    title: "Плаваща по Euribor",
    hint: "Банката преизчислява лихвата на всеки 3, 6 или 12 месеца.",
  },
  {
    value: "BLP",
    title: "Плаваща по БЛП",
    hint: "Банката определя базовия процент сама.",
  },
  {
    value: "FIXED",
    title: "Фиксирана",
    hint: "Лихвата не се променя до края на срока.",
  },
] as const;

const EURIBOR_PERIODS = [
  { value: "EURIBOR_3M" as const, label: "3 месеца" },
  { value: "EURIBOR_6M" as const, label: "6 месеца" },
  { value: "EURIBOR_12M" as const, label: "12 месеца" },
];

const EMPTY: LoanInput = {
  label: "",
  bank_name: BANKS[0],
  loan_type: "MORTGAGE",
  currency: "EUR",
  principal_amount: 100000,
  remaining_months: 240,
  current_interest_rate: 4,
  index_type: "EURIBOR_3M",
  margin: 1.8,
  next_reset_date: null,
};

const STEPS = ["Каква е целта", "Колко и докога", "Каква е лихвата", "Готово"];

function toInput(loan: Loan): LoanInput {
  return {
    label: loan.label,
    bank_name: loan.bank_name,
    loan_type: loan.loan_type,
    currency: loan.currency,
    principal_amount: loan.principal_amount,
    remaining_months: loan.remaining_months,
    current_interest_rate: loan.current_interest_rate,
    index_type: loan.index_type,
    margin: loan.margin,
    next_reset_date: loan.next_reset_date,
  };
}

/** Ануитетна формула — същата като на сървъра, за незабавна обратна връзка. */
function monthlyPayment(principal: number, annualRatePct: number, months: number) {
  if (months <= 0) return 0;
  const rate = annualRatePct / 100 / 12;
  if (rate === 0) return principal / months;
  const factor = (1 + rate) ** months;
  return (principal * rate * factor) / (factor - 1);
}

function Progress({ step }: { step: number }) {
  return (
    <div className="flex items-center gap-2" aria-hidden>
      {STEPS.map((_, index) => (
        <div
          key={index}
          className={cn(
            "h-1 flex-1 rounded-full transition-colors duration-300",
            index <= step ? "bg-primary" : "bg-muted",
          )}
        />
      ))}
    </div>
  );
}

export function LoanWizard({
  initial,
  onSaved,
  onCancel,
}: {
  initial: Loan | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<LoanInput>(
    initial ? toInput(initial) : EMPTY,
  );
  // При редакция показваме всичко наведнъж — човекът вече знае какво търси.
  const [step, setStep] = useState(initial ? 3 : 0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const floating = form.index_type !== "FIXED";
  const isEuribor = form.index_type.startsWith("EURIBOR");

  const payment = useMemo(
    () =>
      monthlyPayment(
        form.principal_amount,
        form.current_interest_rate,
        form.remaining_months,
      ),
    [form.principal_amount, form.current_interest_rate, form.remaining_months],
  );

  function update<K extends keyof LoanInput>(key: K, value: LoanInput[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    setError(null);
    setBusy(true);
    try {
      const payload: LoanInput = {
        ...form,
        label: form.label.trim() || defaultLabel(),
        margin: floating ? form.margin : null,
      };
      if (initial) await api.updateLoan(initial.id, payload);
      else await api.createLoan(payload);
      toast(initial ? "Кредитът е обновен" : "Кредитът е добавен", "success");
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function defaultLabel() {
    return form.loan_type === "MORTGAGE" ? "Жилище" : "Потребителски кредит";
  }

  const canAdvance =
    step === 0
      ? true
      : step === 1
        ? form.principal_amount > 0 && form.remaining_months > 0
        : step === 2
          ? form.current_interest_rate >= 0 &&
            (!floating || (form.margin ?? 0) >= 0)
          : true;

  return (
    <div className="flex flex-col gap-5">
      <Progress step={step} />

      <div>
        <p className="type-caption font-semibold uppercase tracking-wider text-muted-foreground">
          Стъпка {step + 1} от {STEPS.length}
        </p>
        <h2 className="mt-1 type-title-2">{STEPS[step]}</h2>
      </div>

      {/* Ключът на key= кара React да пресъздаде блока, за да се пусне
          анимацията при всяка смяна на стъпката. */}
      <div key={step} className="rise flex flex-col gap-4">
        {step === 0 && (
          <>
            <div>
              <Label htmlFor="w-type">За какво е кредитът</Label>
              <Segmented
                label="Вид кредит"
                value={form.loan_type}
                onChange={(next) => update("loan_type", next as LoanType)}
                options={[
                  { value: "MORTGAGE", label: "Жилище" },
                  { value: "CONSUMER", label: "Потребителски" },
                ]}
              />
            </div>

            <div>
              <Label htmlFor="w-bank">В коя банка</Label>
              <select
                id="w-bank"
                value={form.bank_name}
                onChange={(e) => update("bank_name", e.target.value)}
                className="flex h-11 w-full rounded-[0.75rem] border-0 bg-muted px-3.5 type-body focus-visible:outline-none"
              >
                {BANKS.map((bank) => (
                  <option key={bank} value={bank}>
                    {bank}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label htmlFor="w-label">Как да го наричаме</Label>
              <Input
                id="w-label"
                value={form.label}
                placeholder={defaultLabel()}
                onChange={(e) => update("label", e.target.value)}
              />
              <p className="mt-1 type-caption text-muted-foreground">
                По избор — помага, ако имате повече от един кредит.
              </p>
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <div>
              <Label htmlFor="w-amount">Колко още дължите</Label>
              <Input
                id="w-amount"
                type="number"
                min={1}
                step="any"
                value={form.principal_amount}
                onChange={(e) =>
                  update("principal_amount", Number(e.target.value))
                }
              />
              <p className="mt-1 type-caption text-muted-foreground">
                Оставащата главница, не първоначалната сума. Пише я в
                погасителния план или в онлайн банкирането.
              </p>
            </div>

            <div>
              <Label htmlFor="w-months">За колко месеца още</Label>
              <Input
                id="w-months"
                type="number"
                min={1}
                max={480}
                value={form.remaining_months}
                onChange={(e) =>
                  update("remaining_months", Number(e.target.value))
                }
              />
              <p className="mt-1 type-caption text-muted-foreground">
                {form.remaining_months > 0 &&
                  `Приблизително ${(form.remaining_months / 12).toFixed(1)} години.`}
              </p>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <div>
              <Label htmlFor="w-rate">Каква лихва плащате сега (%)</Label>
              <Input
                id="w-rate"
                type="number"
                min={0}
                step="any"
                value={form.current_interest_rate}
                onChange={(e) =>
                  update("current_interest_rate", Number(e.target.value))
                }
              />
              <p className="mt-1 type-caption text-muted-foreground">
                Числото от договора ви, не ГПР.
              </p>
            </div>

            <fieldset>
              <legend className="mb-1.5 type-subhead font-medium text-muted-foreground">
                Как се определя лихвата
              </legend>
              <div className="flex flex-col gap-2">
                {RATE_KINDS.map((kind) => {
                  const active =
                    kind.value === "EURIBOR_3M"
                      ? isEuribor
                      : form.index_type === kind.value;
                  return (
                    <button
                      key={kind.value}
                      type="button"
                      onClick={() => update("index_type", kind.value)}
                      aria-pressed={active}
                      className={cn(
                        "press flex items-start gap-3 rounded-[0.875rem] p-3 text-left transition-colors",
                        active
                          ? "bg-accent ring-2 ring-primary"
                          : "bg-muted hover:bg-muted/70",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full border-2",
                          active
                            ? "border-primary bg-primary"
                            : "border-muted-foreground/40",
                        )}
                      >
                        {active && (
                          <Check
                            className="h-3 w-3 text-primary-foreground"
                            aria-hidden
                          />
                        )}
                      </span>
                      <span>
                        <span className="block type-subhead font-semibold">
                          {kind.title}
                        </span>
                        <span className="block type-caption text-muted-foreground">
                          {kind.hint}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </fieldset>

            {/* Периодът и надбавката се показват само когато са нужни. */}
            {isEuribor && (
              <div className="rise">
                <Label>На колко се преизчислява</Label>
                <Segmented
                  label="Период на Euribor"
                  value={form.index_type as (typeof EURIBOR_PERIODS)[number]["value"]}
                  onChange={(next) => update("index_type", next)}
                  options={EURIBOR_PERIODS}
                />
              </div>
            )}

            {floating && (
              <div className="rise">
                <Label htmlFor="w-margin">Надбавка над индекса (%)</Label>
                <Input
                  id="w-margin"
                  type="number"
                  step="any"
                  value={form.margin ?? 0}
                  onChange={(e) => update("margin", Number(e.target.value))}
                />
                <p className="mt-1 type-caption text-muted-foreground">
                  Пише в договора като „надбавка“ или „марж“. Ако не сте
                  сигурни, оставете приблизително — прогнозата стъпва на
                  въведената лихва, не на надбавката.
                </p>
              </div>
            )}

            {floating && (
              <div>
                <Label htmlFor="w-reset">
                  Кога банката преизчислява лихвата (по избор)
                </Label>
                <Input
                  id="w-reset"
                  type="date"
                  value={form.next_reset_date ?? ""}
                  onChange={(e) =>
                    update("next_reset_date", e.target.value || null)
                  }
                />
                <p className="mt-1 type-caption text-muted-foreground">
                  Ако я въведете, показваме вноската като непроменена до тази
                  дата — така прогнозата е по-точна.
                </p>
              </div>
            )}
          </>
        )}

        {step === 3 && (
          <div className="flex flex-col gap-3">
            <div className="rounded-[1.125rem] bg-muted p-5">
              <p className="type-subhead text-muted-foreground">
                Месечната ви вноска
              </p>
              <p className="mt-1 type-large-title tabular-nums">
                {money(payment, form.currency)}
              </p>
              <p className="mt-2 type-caption text-muted-foreground">
                {form.label.trim() || defaultLabel()} · {form.bank_name} ·{" "}
                {form.current_interest_rate}% ·{" "}
                {(form.remaining_months / 12).toFixed(1)} години
              </p>
            </div>
            <p className="type-subhead leading-relaxed text-muted-foreground">
              Проверете дали вноската отговаря на това, което плащате в
              действителност. Ако се разминава, най-често причината е грешна
              оставаща главница или срок.
            </p>
          </div>
        )}
      </div>

      {error && <Alert tone="bad">{error}</Alert>}

      <div className="flex items-center gap-2">
        {step > 0 && !initial && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => setStep((s) => s - 1)}
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Назад
          </Button>
        )}

        {step < 3 ? (
          <Button
            type="button"
            className="flex-1"
            disabled={!canAdvance}
            onClick={() => setStep((s) => s + 1)}
          >
            Продължи
          </Button>
        ) : (
          <Button
            type="button"
            className="flex-1"
            disabled={busy}
            onClick={save}
          >
            {busy ? "Запазвам..." : initial ? "Запази промените" : "Добави кредита"}
          </Button>
        )}

        <Button type="button" variant="ghost" onClick={onCancel}>
          Откажи
        </Button>
      </div>
    </div>
  );
}
