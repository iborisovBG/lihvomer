"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Плъзгане наляво разкрива действия — моделът на iOS за списъци.
 *
 * Действията остават достъпни и без плъзгане: те са истински бутони под
 * съдържанието, така че клавиатура и екранен четец стигат до тях по обичайния
 * начин. Плъзгането е удобство, не единствен път.
 */

export interface SwipeAction {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  tone?: "default" | "destructive";
}

// Колко трябва да се плъзне, за да останат действията отворени.
const OPEN_AT_PX = 56;
const ACTION_WIDTH_PX = 76;

export function SwipeActions({
  actions,
  children,
  className,
}: {
  actions: SwipeAction[];
  children: React.ReactNode;
  className?: string;
}) {
  const [offset, setOffset] = React.useState(0);
  const [dragging, setDragging] = React.useState(false);
  const startX = React.useRef<number | null>(null);
  const startOffset = React.useRef(0);
  // Огледало на отместването. При бързо плъзгане React обединява промените и
  // обработчикът при пускане би прочел остаряла стойност от затварянето.
  const currentOffset = React.useRef(0);

  const openWidth = actions.length * ACTION_WIDTH_PX;
  const open = offset > OPEN_AT_PX;

  function apply(next: number) {
    currentOffset.current = next;
    setOffset(next);
  }

  function close() {
    apply(0);
  }

  function onPointerDown(event: React.PointerEvent) {
    // Само за докосване и писалка: с мишка потребителят има бутоните видими.
    if (event.pointerType === "mouse") return;
    startX.current = event.clientX;
    startOffset.current = currentOffset.current;
    setDragging(true);
  }

  function onPointerMove(event: React.PointerEvent) {
    if (startX.current === null) return;
    const delta = startX.current - event.clientX;
    // Плъзга се само наляво и не по-далеч от ширината на действията.
    apply(Math.max(0, Math.min(openWidth, startOffset.current + delta)));
  }

  function onPointerUp() {
    if (startX.current === null) return;
    apply(currentOffset.current > OPEN_AT_PX ? openWidth : 0);
    startX.current = null;
    setDragging(false);
  }

  return (
    <div className={cn("relative overflow-hidden rounded-[1.125rem]", className)}>
      {/* Действията стоят отдолу и се откриват, когато съдържанието се измести. */}
      <div className="absolute inset-y-0 right-0 flex" aria-hidden={!open}>
        {actions.map((action) => (
          <button
            key={action.label}
            type="button"
            tabIndex={open ? 0 : -1}
            onClick={() => {
              action.onClick();
              close();
            }}
            style={{ width: ACTION_WIDTH_PX }}
            className={cn(
              "flex flex-col items-center justify-center gap-1 type-caption font-medium",
              action.tone === "destructive"
                ? "bg-bad text-white"
                : "bg-muted text-foreground",
            )}
          >
            {action.icon}
            {action.label}
          </button>
        ))}
      </div>

      <div
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        style={{ transform: `translateX(-${offset}px)` }}
        className={cn(
          "relative touch-pan-y",
          !dragging && "transition-transform duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]",
        )}
      >
        {children}
      </div>

      {/* Докосване извън действията ги затваря, както в iOS. */}
      {open && (
        <button
          type="button"
          aria-label="Затвори действията"
          onClick={close}
          className="absolute inset-y-0 left-0"
          style={{ right: openWidth }}
        />
      )}
    </div>
  );
}
