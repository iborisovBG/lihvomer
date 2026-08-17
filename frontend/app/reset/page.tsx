"use client";

import { useEffect, useState } from "react";

/**
 * Аварийно изчистване на кеша.
 *
 * Нужно е, защото статичните файлове се отдават с `immutable` за една година.
 * Това е правилно — те носят хеш в името си и не се менят. Но ако някога е
 * било внедрено нещо счупено, браузърът остава с него и няма как да бъде
 * поправен отдалеч.
 *
 * Този адрес е изход от такова състояние: изтрива service worker-а и всички
 * кешове, след което зарежда приложението наново с прясна обвивка. Работи,
 * защото самата страница е адрес, който браузърът няма в кеша си.
 */

type Step = { label: string; done: boolean };

export default function ResetPage() {
  const [steps, setSteps] = useState<Step[]>([
    { label: "Спиране на фоновия процес", done: false },
    { label: "Изтриване на запазените файлове", done: false },
    { label: "Зареждане наново", done: false },
  ]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const mark = (index: number) =>
      setSteps((current) =>
        current.map((step, i) => (i === index ? { ...step, done: true } : step)),
      );

    (async () => {
      try {
        if ("serviceWorker" in navigator) {
          const registrations = await navigator.serviceWorker.getRegistrations();
          await Promise.all(registrations.map((r) => r.unregister()));
        }
        if (cancelled) return;
        mark(0);

        if ("caches" in window) {
          const keys = await caches.keys();
          await Promise.all(keys.map((key) => caches.delete(key)));
        }
        if (cancelled) return;
        mark(1);

        // Адресът носи момента на изчистване, за да не се вземе стара обвивка.
        window.setTimeout(() => {
          mark(2);
          window.location.replace(`${window.location.origin}/?v=${Date.now()}`);
        }, 600);
      } catch (e) {
        setError((e as Error).message);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col justify-center gap-6">
      <div>
        <h1 className="type-title-1">Изчистване на кеша</h1>
        <p className="mt-2 type-subhead text-muted-foreground">
          Браузърът ви е запазил стара версия. Изчистваме я и зареждаме
          приложението наново — това отнема секунда.
        </p>
      </div>

      <ol className="glass list-group">
        {steps.map((step) => (
          <li
            key={step.label}
            className="list-row flex items-center gap-3 px-4 py-3"
          >
            <span
              className={
                step.done
                  ? "grid h-5 w-5 place-items-center rounded-full bg-good text-white"
                  : "h-5 w-5 rounded-full border-2 border-muted-foreground/30"
              }
              aria-hidden
            >
              {step.done ? "✓" : ""}
            </span>
            <span className="type-subhead">{step.label}</span>
          </li>
        ))}
      </ol>

      {error && (
        <p className="type-subhead text-bad">
          Изчистването не мина: {error}. Отворете страницата в режим „инкогнито“
          или изчистете данните за сайта от настройките на браузъра.
        </p>
      )}

      <p className="type-caption text-muted-foreground">
        Ако нищо не се случи до няколко секунди,{" "}
        <a href="/?v=manual" className="text-primary hover:underline">
          продължете към приложението
        </a>
        .
      </p>
    </div>
  );
}
