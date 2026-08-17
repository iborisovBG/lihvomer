"use client";

import * as React from "react";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Панел, който излиза отдолу — моделът на iOS за форми и избор.
 *
 * На телефон се закача за долния ръб и се затваря с плъзгане надолу; на
 * широк екран става центриран диалог. И в двата случая фонът се размива, а
 * фокусът остава вътре, докато панелът е отворен.
 */

const DRAG_CLOSE_PX = 110;

export function Sheet({
  open,
  onClose,
  title,
  description,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  const panelRef = React.useRef<HTMLDivElement>(null);
  const [dragY, setDragY] = React.useState(0);
  const startY = React.useRef<number | null>(null);
  const titleId = React.useId();

  // Escape затваря, а фокусът се връща там, откъдето е дошъл.
  React.useEffect(() => {
    if (!open) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      // Капан за фокуса: Tab не бива да излиза извън панела.
      const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable || focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown, true);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Първото поле получава фокуса, за да може да се пише веднага.
    const timer = window.setTimeout(() => {
      panelRef.current
        ?.querySelector<HTMLElement>(
          'input, select, button:not([data-sheet-close])',
        )
        ?.focus();
    }, 80);

    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      document.body.style.overflow = previousOverflow;
      window.clearTimeout(timer);
      previouslyFocused?.focus?.();
    };
  }, [open, onClose]);

  React.useEffect(() => {
    if (!open) setDragY(0);
  }, [open]);

  if (!open) return null;

  function onPointerDown(event: React.PointerEvent) {
    startY.current = event.clientY;
    (event.target as HTMLElement).setPointerCapture?.(event.pointerId);
  }

  function onPointerMove(event: React.PointerEvent) {
    if (startY.current === null) return;
    // Плъзга се само надолу; нагоре панелът не мърда.
    setDragY(Math.max(0, event.clientY - startY.current));
  }

  function onPointerUp() {
    if (startY.current === null) return;
    if (dragY > DRAG_CLOSE_PX) onClose();
    else setDragY(0);
    startY.current = null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <button
        type="button"
        aria-label="Затвори"
        onClick={onClose}
        className="absolute inset-0 bg-black/25 motion-safe:animate-[fade-in_200ms_ease-out] supports-[backdrop-filter]:backdrop-blur-sm"
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={{ transform: dragY ? `translateY(${dragY}px)` : undefined }}
        className={cn(
          "glass relative flex max-h-[92vh] w-full flex-col",
          "rounded-t-[1.5rem] sm:max-w-lg sm:rounded-[1.5rem]",
          "motion-safe:animate-[sheet-up_320ms_cubic-bezier(0.32,0.72,0,1)]",
          !dragY && "transition-transform duration-200",
        )}
      >
        {/* Дръжката е и зона за плъзгане, и визуален знак, че панелът се дърпа. */}
        <div
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          className="flex cursor-grab touch-none justify-center pb-1 pt-2.5 active:cursor-grabbing sm:hidden"
        >
          <span className="h-1 w-9 rounded-full bg-foreground/20" aria-hidden />
        </div>

        <div className="flex items-start justify-between gap-3 px-5 pb-2 pt-3 sm:pt-5">
          <div className="min-w-0">
            <h2 id={titleId} className="type-title-3">
              {title}
            </h2>
            {description && (
              <p className="mt-0.5 type-subhead text-muted-foreground">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            data-sheet-close
            onClick={onClose}
            aria-label="Затвори"
            className="press grid h-8 w-8 shrink-0 place-items-center rounded-full bg-muted text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div className="overflow-y-auto overscroll-contain px-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-2">
          {children}
        </div>
      </div>
    </div>
  );
}
