"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Check, Info } from "lucide-react";

import { Card, CardContent } from "@/components/ui";
import { api, type Partners } from "@/lib/api";

/**
 * Помощ от човек. Съзнателно е визуално отделена от данните и носи
 * разкриване на комисионата — потребителят трябва да вижда разликата между
 * изчисление и търговско предложение.
 */
export function PartnerCard() {
 const [data, setData] = useState<Partners | null>(null);

 useEffect(() => {
 api.partners().then(setData).catch(() => setData(null));
 }, []);

 if (!data || data.partners.length === 0) return null;

 return (
 <div className="space-y-3">
 {data.partners.map((partner) => (
 <Card key={partner.key} className="border-dashed">
 <CardContent className="pt-5">
 <div className="flex flex-wrap items-start justify-between gap-3">
 <div>
 <div className="type-caption font-semibold uppercase tracking-wider text-muted-foreground">
 Партньор · реклама
 </div>
 <h3 className="mt-1 type-title-3">{partner.name}</h3>
 <p className="type-subhead text-muted-foreground">
 {partner.role_bg}
 </p>
 </div>
 <a
 href={partner.url}
 target="_blank"
 rel="noopener noreferrer nofollow sponsored"
 className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 type-subhead font-medium text-primary-foreground transition-colors hover:bg-primary/90"
 >
 Към сайта
 <ArrowUpRight className="h-4 w-4" />
 </a>
 </div>

 <p className="mt-3 type-subhead leading-relaxed">
 {partner.what_they_do_bg}
 </p>

 {partner.good_fit_bg.length > 0 && (
 <ul className="mt-3 space-y-1.5">
 {partner.good_fit_bg.map((item) => (
 <li key={item} className="flex gap-2 type-subhead">
 <Check
 className="mt-0.5 h-4 w-4 shrink-0 text-primary"
 aria-hidden
 />
 <span className="text-muted-foreground">{item}</span>
 </li>
 ))}
 </ul>
 )}

 <div className="mt-4 flex gap-2 rounded-xl bg-muted p-3">
 <Info
 className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
 aria-hidden
 />
 <p className="type-caption leading-relaxed text-muted-foreground">
 {partner.disclosure_bg}
 </p>
 </div>
 </CardContent>
 </Card>
 ))}

 <p className="px-1 type-caption leading-relaxed text-muted-foreground">
 {data.general_note_bg}
 </p>
 </div>
 );
}
