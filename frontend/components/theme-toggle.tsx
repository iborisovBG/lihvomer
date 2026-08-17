"use client";

import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";

import { cn } from "@/lib/utils";

type Theme = "light" | "dark" | "system";

const KEY = "lihvomer_theme";

const OPTIONS: { value: Theme; label: string; Icon: typeof Sun }[] = [
 { value: "light", label: "Светла тема", Icon: Sun },
 { value: "system", label: "Според системата", Icon: Monitor },
 { value: "dark", label: "Тъмна тема", Icon: Moon },
];

/** Винаги оставя явен data-theme: класовете dark: на Tailwind четат него. */
export function applyTheme(theme: Theme) {
 const dark =
 theme === "dark" ||
 (theme === "system" &&
 window.matchMedia("(prefers-color-scheme: dark)").matches);
 document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
}

export function ThemeToggle() {
 const [theme, setTheme] = useState<Theme>("system");

 useEffect(() => {
 const stored = (window.localStorage.getItem(KEY) as Theme | null) ?? "system";
 setTheme(stored);
 applyTheme(stored);

 // При избрана „системна" следим промените в настройката на устройството.
 const media = window.matchMedia("(prefers-color-scheme: dark)");
 const onChange = () => {
 const current =
 (window.localStorage.getItem(KEY) as Theme | null) ?? "system";
 if (current === "system") applyTheme("system");
 };
 media.addEventListener("change", onChange);
 return () => media.removeEventListener("change", onChange);
 }, []);

 function choose(next: Theme) {
 setTheme(next);
 window.localStorage.setItem(KEY, next);
 applyTheme(next);
 }

 return (
 <div
 role="radiogroup"
 aria-label="Тема на приложението"
 className="inline-flex rounded-lg border border-border p-0.5"
 >
 {OPTIONS.map(({ value, label, Icon }) => (
 <button
 key={value}
 type="button"
 role="radio"
 aria-checked={theme === value}
 aria-label={label}
 title={label}
 onClick={() => choose(value)}
 className={cn(
 "grid h-7 w-7 place-items-center rounded-md transition-colors",
 "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
 theme === value
 ? "bg-accent text-primary"
 : "text-muted-foreground hover:text-foreground",
 )}
 >
 <Icon className="h-3.5 w-3.5" aria-hidden />
 </button>
 ))}
 </div>
 );
}
