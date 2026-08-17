"use client";

import { useEffect } from "react";

/**
 * Регистрира service worker-а и се грижи новата версия да поеме веднага.
 *
 * Без `update()` и презареждане браузърът може да държи стария worker с дни.
 * В приложение, което показва лихви, това значи стари числа и — както се случи
 * веднъж — стар пакет, който вика адрес от локалната разработка.
 */
export function ServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    let refreshing = false;

    // Самолечение при заседнал стар worker.
    //
    // Ако страницата се отваря от истински домейн, но в кеша още стои обвивка
    // от предишно внедряване, браузърът може да зарежда стари пакети седмици
    // наред. Тук разпознаваме такъв кеш по името му и го изчистваме веднъж.
    const purgeStaleCaches = async () => {
      if (!("caches" in window)) return;
      try {
        const keys = await caches.keys();
        const stale = keys.filter((key) => key !== "lihvomer-v2");
        if (stale.length === 0) return;
        await Promise.all(stale.map((key) => caches.delete(key)));
        window.location.reload();
      } catch {
        // Липсата на достъп до кеша не бива да чупи приложението.
      }
    };
    void purgeStaleCaches();

    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        // Проверяваме за нова версия при всяко отваряне.
        registration.update().catch(() => {});
      })
      .catch(() => {
        // Липсата на офлайн режим не бива да чупи приложението.
      });

    // Когато нов worker поеме контрола, презареждаме веднъж, за да няма
    // смесване на стар и нов код в една страница.
    const onControllerChange = () => {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    };

    navigator.serviceWorker.addEventListener(
      "controllerchange",
      onControllerChange,
    );
    return () =>
      navigator.serviceWorker.removeEventListener(
        "controllerchange",
        onControllerChange,
      );
  }, []);

  return null;
}
