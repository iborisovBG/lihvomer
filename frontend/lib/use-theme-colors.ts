"use client";

import { useEffect, useState } from "react";

/**
 * Чете системните цветове от CSS променливите по време на изпълнение.
 *
 * Recharts иска конкретни стойности за `stroke` и `fill`, а не CSS променливи.
 * Затова ги прочитаме от документа и ги преизчисляваме при смяна на темата —
 * така графиките следват избора на потребителя, вместо да носят зашити цветове.
 */

const TOKENS = {
  primary: "--sys-blue",
  good: "--good",
  warn: "--warn",
  bad: "--bad",
  label: "--foreground",
  muted: "--muted-foreground",
  grid: "--border",
} as const;

export type ThemeColors = Record<keyof typeof TOKENS, string>;

// Стойности за първото рисуване на сървъра, преди да има документ.
const FALLBACK: ThemeColors = {
  primary: "hsl(211 100% 50%)",
  good: "hsl(142 71% 45%)",
  warn: "hsl(28 100% 52%)",
  bad: "hsl(3 100% 59%)",
  label: "hsl(0 0% 0%)",
  muted: "hsl(240 6% 42%)",
  grid: "hsl(240 12% 88%)",
};

function read(): ThemeColors {
  const styles = getComputedStyle(document.documentElement);
  const result = {} as ThemeColors;
  for (const [key, token] of Object.entries(TOKENS)) {
    const raw = styles.getPropertyValue(token).trim();
    result[key as keyof ThemeColors] = raw
      ? `hsl(${raw})`
      : FALLBACK[key as keyof ThemeColors];
  }
  return result;
}

export function useThemeColors(): ThemeColors {
  const [colors, setColors] = useState<ThemeColors>(FALLBACK);

  useEffect(() => {
    setColors(read());

    // Превключвателят сменя data-theme върху <html>; следим го.
    const observer = new MutationObserver(() => setColors(read()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);

  return colors;
}
