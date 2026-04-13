"use client";

import type { CityComparison } from "@/lib/types";
import { formatPct, formatSilver } from "@/lib/format";

interface CityComparisonProps {
  cities: CityComparison[];
  bestCity: string;
}

export default function CityComparisonTable({ cities, bestCity }: CityComparisonProps) {
  const sorted = [...cities].sort((a, b) => {
    if (a.return_rate_pct === null && b.return_rate_pct === null) return 0;
    if (a.return_rate_pct === null) return 1;
    if (b.return_rate_pct === null) return -1;
    return b.return_rate_pct - a.return_rate_pct;
  });

  const withData = sorted.filter((c) => c.return_rate_pct !== null);
  const withoutData = sorted.filter((c) => c.return_rate_pct === null);

  const maxProfit = Math.max(
    ...sorted
      .map((c) => c.profit_absolute)
      .filter((v): v is number => v !== null && v > 0),
    1,
  );

  return (
    <div className="space-y-3">
      {/* City cards grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {withData.map((city, idx) => {
          const isBest = city.city === bestCity;
          const isPositive = city.return_rate_pct! > 0.5;
          const isNegative = city.return_rate_pct! < -0.5;
          const profitBarWidth =
            city.profit_absolute !== null && city.profit_absolute > 0
              ? (city.profit_absolute / maxProfit) * 100
              : 0;

          return (
            <div
              key={city.city}
              className="relative overflow-hidden rounded-lg border"
              style={{
                background: "var(--color-bg-elevated)",
                borderColor: isBest
                  ? "var(--color-accent-gold)"
                  : "var(--color-border-default)",
                borderWidth: isBest ? "2px" : "1px",
              }}
            >
              {/* Rank + City header */}
              <div
                className="flex items-center justify-between px-4 py-2.5"
                style={{
                  background: isBest ? "var(--color-accent-gold)" : "var(--color-bg-panel)",
                  borderBottom: `1px solid ${isBest ? "var(--color-accent-gold)" : "var(--color-border-default)"}`,
                }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold"
                    style={{
                      background: isBest ? "rgba(0,0,0,0.25)" : "var(--color-bg-elevated)",
                      color: isBest ? "#fff" : "var(--color-text-muted)",
                    }}
                  >
                    {idx + 1}
                  </span>
                  <span
                    className="text-sm font-semibold"
                    style={{ color: isBest ? "#1a1a1a" : "var(--color-text-primary)" }}
                  >
                    {city.city}
                  </span>
                </div>
                {isBest && (
                  <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "#1a1a1a" }}>
                    Melhor
                  </span>
                )}
              </div>

              {/* Metrics */}
              <div className="space-y-3 px-4 py-3">
                {/* Return rate */}
                <div className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    Retorno
                  </span>
                  <span
                    className="tabular-nums inline-block rounded px-2 py-0.5 text-sm font-bold"
                    style={{
                      fontFamily: "var(--font-plex-mono), monospace",
                      background: isPositive
                        ? "var(--color-profit-soft)"
                        : isNegative
                          ? "var(--color-loss-soft)"
                          : "var(--color-info-soft)",
                      color: isPositive
                        ? "var(--color-profit-strong)"
                        : isNegative
                          ? "var(--color-loss-strong)"
                          : "var(--color-info)",
                    }}
                  >
                    {formatPct(city.return_rate_pct!)}
                  </span>
                </div>

                {/* Sell price */}
                <div className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                    Preço de Venda
                  </span>
                  <span
                    className="tabular-nums text-sm font-medium"
                    style={{
                      fontFamily: "var(--font-plex-mono), monospace",
                      color: "var(--color-text-primary)",
                    }}
                  >
                    {city.sell_price !== null ? formatSilver(city.sell_price) : "—"}
                  </span>
                </div>

                {/* Profit with bar */}
                <div>
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                      Lucro
                    </span>
                    <span
                      className="tabular-nums text-sm font-bold"
                      style={{
                        fontFamily: "var(--font-plex-mono), monospace",
                        color:
                          city.profit_absolute !== null && city.profit_absolute >= 0
                            ? "var(--color-profit-strong)"
                            : "var(--color-loss-strong)",
                      }}
                    >
                      {city.profit_absolute !== null ? formatSilver(city.profit_absolute) : "—"}
                    </span>
                  </div>
                  {profitBarWidth > 0 && (
                    <div
                      className="h-1 rounded-full"
                      style={{ background: "var(--color-border-muted)" }}
                    >
                      <div
                        className="h-1 rounded-full transition-all"
                        style={{
                          width: `${profitBarWidth}%`,
                          background: "var(--color-profit-strong)",
                        }}
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Cities without data */}
      {withoutData.length > 0 && (
        <div
          className="flex flex-wrap items-center gap-2 rounded-lg px-4 py-2.5"
          style={{ background: "var(--color-bg-panel)" }}
        >
          <span className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
            Sem dados:
          </span>
          {withoutData.map((city) => (
            <span
              key={city.city}
              className="rounded-md border px-2.5 py-1 text-xs"
              style={{
                borderColor: "var(--color-border-muted)",
                color: "var(--color-text-muted)",
              }}
            >
              {city.city}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
