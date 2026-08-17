"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";

import { api, type Sources } from "@/lib/api";

export function Footer() {
 const [sources, setSources] = useState<Sources | null>(null);

 useEffect(() => {
 api.sources().then(setSources).catch(() => setSources(null));
 }, []);

 return (
 <footer className="mt-12 border-t border-border bg-surface">
 <div className="mx-auto w-full max-w-6xl px-4 py-8">
 <div className="grid gap-8 md:grid-cols-[1.4fr_1fr]">
 <div>
 <div className="flex items-center gap-2">
 <ShieldCheck className="h-4 w-4 text-primary" aria-hidden />
 <h2 className="type-subhead font-semibold">
 Как да четете тези числа
 </h2>
 </div>
 <p className="mt-2 max-w-prose type-subhead leading-relaxed text-muted-foreground">
 {sources?.disclaimer_bg ??
 "Всички изчисления в приложението стъпват изцяло на публично достъпни официални данни. Те нямат за цел да плашат, стряскат или да дават финансов съвет на когото и да било. Прогнозите са статистическа оценка с посочена несигурност, а не обещание. Преди решение за кредит се консултирайте с вашата банка или с лицензиран консултант."}
 </p>
 <p className="mt-3 max-w-prose type-caption leading-relaxed text-muted-foreground">
 Всеки показател носи датата, на която е публикуван, и линк към
 оригиналния източник — можете да проверите всяко число сами.
 </p>
 </div>

 <div>
 <h2 className="type-subhead font-semibold">Откъде идват данните</h2>
 <ul className="mt-2 space-y-1.5">
 {(sources?.providers ?? []).map((provider) => (
 <li key={provider.key} className="type-subhead">
 <a
 href={provider.portal_url}
 target="_blank"
 rel="noopener noreferrer"
 className="text-muted-foreground transition-colors hover:text-primary"
 >
 {provider.name_bg}
 </a>
 <span className="ml-1.5 type-caption text-muted-foreground">
 ({provider.series.length}{" "}
 {provider.series.length === 1 ? "показател" : "показателя"})
 </span>
 </li>
 ))}
 </ul>
 <Link
 href="/sources"
 className="mt-3 inline-block type-subhead font-medium text-primary hover:underline"
 >
 Пълен списък на източниците →
 </Link>
 </div>
 </div>

 <div className="mt-8 border-t border-border pt-4 type-caption text-muted-foreground">
 Лихвомер · данните са собственост на съответните институции и се
 ползват съгласно техните условия за свободно ползване.
 </div>
 </div>
 </footer>
 );
}
