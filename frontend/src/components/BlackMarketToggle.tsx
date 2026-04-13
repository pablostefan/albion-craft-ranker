"use client";

import { useCallback, useRef } from "react";
import type { MarketMode } from "@/lib/types";

const MODES: { value: MarketMode; label: string }[] = [
  { value: "marketplace", label: "Mercado" },
  { value: "black_market", label: "Mercado Negro" },
  { value: "comparison", label: "Comparação" },
];

interface BlackMarketToggleProps {
  value: MarketMode;
  onChange: (mode: MarketMode) => void;
}

export default function BlackMarketToggle({ value, onChange }: BlackMarketToggleProps) {
  const groupRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const idx = MODES.findIndex((m) => m.value === value);
      let next = idx;

      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        next = (idx + 1) % MODES.length;
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        next = (idx - 1 + MODES.length) % MODES.length;
      } else {
        return;
      }

      onChange(MODES[next].value);

      const buttons = groupRef.current?.querySelectorAll<HTMLButtonElement>(
        '[role="radio"]',
      );
      buttons?.[next]?.focus();
    },
    [value, onChange],
  );

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      aria-label="Modo de mercado"
      className="flex rounded-lg border"
      style={{
        background: "var(--color-bg-canvas)",
        borderColor: "var(--color-border-default)",
      }}
      onKeyDown={handleKeyDown}
    >
      {MODES.map((mode) => {
        const isSelected = mode.value === value;
        return (
          <button
            key={mode.value}
            role="radio"
            aria-checked={isSelected}
            tabIndex={isSelected ? 0 : -1}
            onClick={() => onChange(mode.value)}
            className="flex-1 px-3 py-2 text-xs font-medium transition-colors first:rounded-l-md last:rounded-r-md"
            style={{
              background: isSelected ? "var(--color-bg-overlay)" : "transparent",
              color: isSelected
                ? "var(--color-accent-gold)"
                : "var(--color-text-muted)",
              borderRight:
                mode.value !== "comparison"
                  ? "1px solid var(--color-border-default)"
                  : undefined,
            }}
          >
            {mode.label}
          </button>
        );
      })}
    </div>
  );
}
