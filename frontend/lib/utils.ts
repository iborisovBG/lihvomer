import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const BGN_PER_EUR = 1.95583;

/** Легаси кредити, въведени в лева, се показват в евро по фиксинга на БНБ. */
export function toEur(amount: number, currency: "BGN" | "EUR") {
  return currency === "EUR" ? amount : amount / BGN_PER_EUR;
}

export function money(amount: number, currency: "BGN" | "EUR" = "EUR") {
  return new Intl.NumberFormat("bg-BG", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function percent(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "няма данни";
  return `${value.toFixed(digits).replace(".", ",")}%`;
}

/** Знак и число без валутен символ — за тесни клетки в таблици. */
export function signedNumber(amount: number, digits = 0) {
  const sign = amount > 0 ? "+" : amount < 0 ? "−" : "";
  return `${sign}${Math.abs(amount).toFixed(digits)}`;
}

export function signedMoney(amount: number, currency: "BGN" | "EUR" = "EUR") {
  const sign = amount > 0 ? "+" : amount < 0 ? "−" : "";
  return `${sign}${money(Math.abs(amount), currency)}`;
}

export function formatDate(iso: string) {
  return new Intl.DateTimeFormat("bg-BG", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(iso));
}

export function shortDate(iso: string) {
  return new Intl.DateTimeFormat("bg-BG", {
    month: "2-digit",
    year: "2-digit",
  }).format(new Date(iso));
}

/** Тримесечията се съхраняват като първия ден от периода; показваме ги четимо. */
export function quarterLabel(iso: string | null, isQuarterly: boolean) {
  if (!iso) return "няма данни";
  const d = new Date(iso);
  if (!isQuarterly) return String(d.getFullYear());
  const quarter = Math.floor(d.getMonth() / 3) + 1;
  return `${quarter}-во тримесечие на ${d.getFullYear()} г.`;
}

export function relativeTime(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.round(diffMs / 3_600_000);
  if (hours < 1) return "преди по-малко от час";
  if (hours < 24) return `преди ${hours} ч.`;
  const days = Math.round(hours / 24);
  if (days === 1) return "вчера";
  if (days < 30) return `преди ${days} дни`;
  return formatDate(iso);
}
