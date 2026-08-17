"use client";

import * as React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Компоненти в езика на iOS.
 *
 * Не само матово стъкло: сегментен контрол вместо падащи менюта, групирани
 * списъци с разделители, които започват след иконата, и лента за съобщения,
 * която идва отдолу и си отива сама.
 */

// --- Лента за съобщения (snack bar) -----------------------------------------

type ToastTone = "default" | "success" | "error";

interface ToastMessage {
 id: number;
 text: string;
 tone: ToastTone;
}

const ToastContext = React.createContext<
 ((text: string, tone?: ToastTone) => void) | null
>(null);

export function useToast() {
 const show = React.useContext(ToastContext);
 if (!show) {
 throw new Error("useToast изисква <ToastHost> нагоре по дървото.");
 }
 return show;
}

const TOAST_MS = 3200;

export function ToastHost({ children }: { children: React.ReactNode }) {
 const [messages, setMessages] = React.useState<ToastMessage[]>([]);

 const show = React.useCallback((text: string, tone: ToastTone = "default") => {
 const id = Date.now() + Math.random();
 setMessages((current) => [...current, { id, text, tone }]);
 window.setTimeout(
 () => setMessages((current) => current.filter((m) => m.id !== id)),
 TOAST_MS,
 );
 }, []);

 return (
 <ToastContext.Provider value={show}>
 {children}
 <div
 aria-live="polite"
 aria-atomic="true"
 className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex flex-col items-center gap-2 px-4 md:bottom-8"
 >
 {messages.map((message) => (
 <div
 key={message.id}
 role="status"
 className={cn(
 "glass pointer-events-auto flex max-w-sm items-center gap-2.5",
 "rounded-full px-4 py-2.5 type-subhead font-medium shadow-lg",
 "motion-safe:animate-[toast-in_220ms_cubic-bezier(0.32,0.72,0,1)]",
 message.tone === "success" &&
 "text-good",
 message.tone === "error" && "text-bad",
 )}
 >
 <span
 className={cn(
 "h-2 w-2 shrink-0 rounded-full",
 message.tone === "success" && "bg-good",
 message.tone === "error" && "bg-bad",
 message.tone === "default" && "bg-primary",
 )}
 aria-hidden
 />
 {message.text}
 </div>
 ))}
 </div>
 </ToastContext.Provider>
 );
}

// --- Сегментен контрол ------------------------------------------------------

export function Segmented<T extends string>({
 value,
 onChange,
 options,
 label,
 className,
}: {
 value: T;
 onChange: (next: T) => void;
 options: { value: T; label: string }[];
 label: string;
 className?: string;
}) {
 return (
 <div
 role="radiogroup"
 aria-label={label}
 className={cn(
 "inline-flex w-full rounded-xl bg-muted p-1 type-subhead",
 className,
 )}
 >
 {options.map((option) => {
 const active = option.value === value;
 return (
 <button
 key={option.value}
 type="button"
 role="radio"
 aria-checked={active}
 onClick={() => onChange(option.value)}
 className={cn(
 "flex-1 rounded-lg px-3 py-1.5 font-medium transition-all",
 "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
 active
 ? "bg-card text-foreground shadow-sm"
 : "text-muted-foreground hover:text-foreground",
 )}
 >
 {option.label}
 </button>
 );
 })}
 </div>
 );
}

// --- Групиран списък --------------------------------------------------------

export function ListGroup({
 header,
 footer,
 children,
}: {
 header?: string;
 footer?: string;
 children: React.ReactNode;
}) {
 return (
 <section className="flex flex-col gap-1.5">
 {header && (
 <h3 className="px-4 type-caption font-semibold uppercase tracking-wider text-muted-foreground">
 {header}
 </h3>
 )}
 <div className="glass overflow-hidden rounded-2xl">{children}</div>
 {footer && (
 <p className="px-4 type-caption leading-relaxed text-muted-foreground">
 {footer}
 </p>
 )}
 </section>
 );
}

export function ListRow({
 title,
 subtitle,
 value,
 onClick,
 href,
 trailing,
}: {
 title: string;
 subtitle?: string;
 value?: React.ReactNode;
 onClick?: () => void;
 href?: string;
 trailing?: React.ReactNode;
}) {
 const interactive = Boolean(onClick || href);

 const inner = (
 <>
 <div className="min-w-0 flex-1">
 <div className="truncate type-subhead font-medium">{title}</div>
 {subtitle && (
 <div className="mt-0.5 type-caption text-muted-foreground">{subtitle}</div>
 )}
 </div>
 {value !== undefined && (
 <div className="shrink-0 type-subhead tabular-nums text-muted-foreground">
 {value}
 </div>
 )}
 {trailing}
 {interactive && !trailing && (
 <ChevronRight
 className="h-4 w-4 shrink-0 text-muted-foreground"
 aria-hidden
 />
 )}
 </>
 );

 // Разделителят започва след отстъпа, както в iOS, а не от ръба на картата.
 const classes = cn(
 "flex w-full items-center gap-3 px-4 py-3 text-left",
 "border-b border-border/60 last:border-0",
 interactive && "transition-colors hover:bg-muted/60 active:bg-muted",
 "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
 );

 if (href) {
 return (
 <a href={href} className={classes}>
 {inner}
 </a>
 );
 }
 if (onClick) {
 return (
 <button type="button" onClick={onClick} className={classes}>
 {inner}
 </button>
 );
 }
 return <div className={classes}>{inner}</div>;
}

// --- Сгъваем панел ----------------------------------------------------------

/**
 * Инструмент, който стои затворен, докато не потрябва.
 *
 * Разликата с диагнозата е важна: отговорът трябва да се вижда веднага, а
 * калкулаторите — само когато човекът реши да смята. Четири отворени форми на
 * един екран изглеждат като работа, която му предстои.
 */
export function Disclosure({
  title,
  summary,
  icon,
  defaultOpen = false,
  children,
}: {
  title: string;
  summary?: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  const contentId = React.useId();

  return (
    <div className="glass overflow-hidden rounded-[1.125rem]">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={contentId}
        className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
      >
        {icon && <span className="shrink-0 text-primary">{icon}</span>}
        <span className="min-w-0 flex-1">
          <span className="block type-headline">{title}</span>
          {summary && (
            <span className="mt-0.5 block type-subhead text-muted-foreground">
              {summary}
            </span>
          )}
        </span>
        <ChevronDown
          className={cn(
            "h-5 w-5 shrink-0 text-muted-foreground transition-transform duration-200",
            open && "rotate-180",
          )}
          aria-hidden
        />
      </button>

      {open && (
        <div id={contentId} className="rise border-t border-border/60 px-5 py-4">
          {children}
        </div>
      )}
    </div>
  );
}
