"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

import type { MacroIndicator } from "@/lib/api";
import { useThemeColors } from "@/lib/use-theme-colors";
import { cn, formatDate, percent } from "@/lib/utils";

/**
 * Показателите, подредени по въпроса, на който отговарят, а не по източника,
 * от който идват. Човек не търси „ЕЦБ MIR" — търси какво движи вноската му.
 *
 * Всяка карта носи спарклайн: посоката на реда казва повече от едно число.
 */

const GROUPS: { title: string; hint: string; codes: string[] }[] = [
  {
    title: "Какво движи лихвата ми",
    hint: "Тези редове стигат до вноската ви със закъснение от няколко месеца.",
    codes: [
      "BG_MORTGAGE_EUR",
      "EURIBOR_3M",
      "EURIBOR_6M",
      "EURIBOR_12M",
      "DE10Y_BUND",
      "ECB_DFR",
      "BG_CONSUMER_EUR",
      "BG_MORTGAGE_APRC",
      "BG_CONSUMER_APRC",
      "EA_AAA_10Y",
      "US_10Y",
    ],
  },
  {
    title: "Какво става с цените",
    hint: "Инфлацията решава дали кредитът ви реално олеква, или тежи.",
    codes: ["HICP_BG", "HICP_EU", "BG_HOUSE_PRICES"],
  },
  {
    title: "Колко печелят спестяванията",
    hint: "Ако лихвата е под инфлацията, парите ви губят стойност.",
    codes: ["BG_DEPOSIT_TERM", "BG_DEPOSIT_OVERNIGHT"],
  },
  {
    title: "Какво прави държавата",
    hint: "Фискалното състояние стига до лихвите през цената на дълга.",
    codes: [
      "BG_GOV_DEBT_Q",
      "BG_GOV_BALANCE_Q",
      "BG_10Y_GOVT_EUR",
      "DE_10Y_GOVT_M",
      "BG_GOV_DEBT",
      "BG_GOV_BALANCE",
      "BG_MORTGAGE_VOLUME",
    ],
  },
];

function unitSuffix(unit: string) {
  if (unit === "PERCENT_OF_GDP") return "% от БВП";
  if (unit === "MILLION_EUR") return "млн. €";
  return "%";
}

/** Малка линия от последните наблюдения. Нормира се към собствения си обхват. */
function Sparkline({ values, tone }: { values: number[]; tone: string }) {
  if (values.length < 2) return null;

  const width = 72;
  const height = 22;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - min) / span) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const last = points[points.length - 1].split(",");

  return (
    <svg
      viewBox={`0 -2 ${width} ${height + 4}`}
      className="h-6 w-[72px] overflow-visible"
      aria-hidden
    >
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke={tone}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.7}
      />
      {/* Последната точка се подчертава — тя е днешното състояние. */}
      <circle cx={last[0]} cy={last[1]} r={2.2} fill={tone} />
    </svg>
  );
}

function IndicatorRow({ indicator }: { indicator: MacroIndicator }) {
  const [open, setOpen] = useState(false);
  const colors = useThemeColors();
  const change = indicator.change;
  const rising = change !== null && change > 0;
  const falling = change !== null && change < 0;

  // Посоката се оцветява спрямо това как влияе на кредитополучателя.
  const tone = rising ? colors.bad : falling ? colors.good : colors.muted;

  return (
    <div className="list-row">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        <div className="min-w-0 flex-1">
          <div className="type-subhead font-medium leading-tight">
            {indicator.name_bg}
          </div>
          {indicator.latest_date && (
            <div className="mt-0.5 type-caption text-muted-foreground">
              към {formatDate(indicator.latest_date)}
            </div>
          )}
        </div>

        <Sparkline values={indicator.spark} tone={tone} />

        <div className="shrink-0 text-right">
          <div className="type-body font-semibold tabular-nums">
            {indicator.latest_value === null
              ? "—"
              : indicator.latest_value.toFixed(2).replace(".", ",")}
            <span className="ml-0.5 type-caption font-normal text-muted-foreground">
              {unitSuffix(indicator.unit)}
            </span>
          </div>
          {change !== null && (
            <div
              className={cn(
                "type-caption tabular-nums",
                rising && "text-bad",
                falling && "text-good",
                !rising && !falling && "text-muted-foreground",
              )}
            >
              {rising ? "▲" : falling ? "▼" : "■"}{" "}
              {Math.abs(change).toFixed(2).replace(".", ",")}
            </div>
          )}
        </div>

        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
            open && "rotate-180",
          )}
          aria-hidden
        />
      </button>

      {open && (
        <div className="rise border-t border-border/60 bg-muted/40 px-4 py-3">
          <p className="type-caption leading-relaxed text-muted-foreground">
            {indicator.plain_bg}
          </p>
          <p className="mt-1.5 type-caption text-muted-foreground">
            Източник: {indicator.source} · {indicator.source_ref}
          </p>
        </div>
      )}
    </div>
  );
}

export function KpiGrid({
  indicators,
  realRate,
}: {
  indicators: MacroIndicator[];
  realRate: number | null;
}) {
  const byCode = new Map(indicators.map((i) => [i.code, i]));
  const grouped = GROUPS.map((group) => ({
    ...group,
    items: group.codes
      .map((code) => byCode.get(code))
      .filter((item): item is MacroIndicator => item !== undefined),
  })).filter((group) => group.items.length > 0);

  const placed = new Set(grouped.flatMap((g) => g.items.map((i) => i.code)));
  const rest = indicators.filter((i) => !placed.has(i.code));

  return (
    <div className="flex flex-col gap-5">
      {realRate !== null && (
        <div className="glass glass-specular rounded-[1.125rem] p-5">
          <div className="type-subhead text-muted-foreground">
            Реален лихвен процент
          </div>
          <div className="mt-1 type-title-1 tabular-nums">
            {percent(realRate)}
          </div>
          <p className="mt-1 type-caption leading-relaxed text-muted-foreground">
            {realRate < 0
              ? "Инфлацията изпреварва лихвата — дългът ви реално олеква."
              : "Лихвата изпреварва инфлацията — кредитът реално ви струва."}
          </p>
        </div>
      )}

      {grouped.map((group) => (
        <section key={group.title} className="flex flex-col gap-1.5">
          <h3 className="px-1 type-caption font-semibold uppercase tracking-wider text-muted-foreground">
            {group.title}
          </h3>
          <div className="glass list-group">
            {group.items.map((indicator) => (
              <IndicatorRow key={indicator.code} indicator={indicator} />
            ))}
          </div>
          <p className="px-1 type-caption leading-relaxed text-muted-foreground">
            {group.hint}
          </p>
        </section>
      ))}

      {rest.length > 0 && (
        <section className="flex flex-col gap-1.5">
          <h3 className="px-1 type-caption font-semibold uppercase tracking-wider text-muted-foreground">
            Останали показатели
          </h3>
          <div className="glass list-group">
            {rest.map((indicator) => (
              <IndicatorRow key={indicator.code} indicator={indicator} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
