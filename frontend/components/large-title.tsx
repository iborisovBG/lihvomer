"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Заглавие в стила на iOS: голямо в началото на страницата, а при скрол се
 * свива и минава в лентата отгоре. Така потребителят винаги знае къде е, без
 * заглавието да заема място през цялото време.
 */
/** Височината на горната лента; под нея заглавието се смята за скрито. */
const NAV_HEIGHT_PX = 64;

export function LargeTitle({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  const sentinel = useRef<HTMLDivElement>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const node = sentinel.current;
    if (!node) return;

    // Измерваме направо в обработчика. Едно четене на позиция е евтино, а
    // requestAnimationFrame не се изпълнява в скрит раздел — там свиването
    // би замръзвало в грешно състояние.
    const measure = () => {
      setCollapsed(node.getBoundingClientRect().bottom < NAV_HEIGHT_PX);
    };

    measure();
    window.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure, { passive: true });
    return () => {
      window.removeEventListener("scroll", measure);
      window.removeEventListener("resize", measure);
    };
  }, []);

  return (
    <>
      {/* Свитото заглавие се появява в лентата, когато голямото си отиде. */}
      <div
        aria-hidden={!collapsed}
        className={cn(
          "glass-bar pointer-events-none fixed inset-x-0 top-[57px] z-20 border-b px-4 py-2.5",
          "transition-all duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
          collapsed
            ? "translate-y-0 opacity-100"
            : "pointer-events-none -translate-y-2 opacity-0",
        )}
      >
        <div className="mx-auto w-full max-w-6xl">
          <span className="type-headline">{title}</span>
        </div>
      </div>

      <div ref={sentinel} className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="type-large-title">{title}</h1>
          {description && (
            <p className="mt-1 max-w-prose type-subhead text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        {action}
      </div>
    </>
  );
}
