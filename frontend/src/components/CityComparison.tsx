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

  const maxProfit = Math.max(
    ...sorted
      .map((c) => c.profit_absolute)
      .filter((v): v is number => v !== null && v > 0),
    1,
  );

  return (
    <div
      className="overflow-x-auto rounded-lg border"
      style={{
        background: "var(--color-bg-elevated)",
        borderColor: "var(--color-border-default)",
      }}
    >
      <table className="w-full text-sm" style={{ color: "var(--color-text-primary)" }}>
        <thead>
          <tr
            style={{
              background: "var(--color-bg-panel)",
              borderBottom: "1px solid var(--color-border-default)",
            }}
          >
            <th scope="col" className="px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>
              Cidade
            </th>
            <th scope="col" className="px-4 py-3 text-right text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>
              Retorno %
            </th>
            <th scope="col" className="px-4 py-3 text-right text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>
              Lucro
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((city) => {
            const isBest = city.city === bestCity;
            const hasData = city.return_rate_pct !== null;
            const isPositive = hasData && city.return_rate_pct! > 0.5;
            const isNegative = hasData && city.return_rate_pct! < -0.5;
            const profitBarWidth =
              city.profit_absolute !== null && city.profit_absolute > 0
                ? (city.profit_absolute / maxProfit) * 100
                : 0;

            return (
              <tr
                key={city.city}
                style={{
                  borderBottom: "1px solid var(--color-border-muted)",
                  borderLeft: isBest
                    ? "3px solid var(--color-accent-gold)"
                    : "3px solid transparent",
                  background: isBest ? "var(--color-bg-panel)" : undefined,
                }}
              >
                <td className="px-4 py-3 text-sm font-medium">
                  <span className="flex items-center gap-2">
                    {city.city}
                    {isBest && (
                      <span
                        className="text-xs"
                        style={{ color: "var(--color-accent-gold)" }}
                        aria-label="Melhor cidade"
                      >
                        ⭐
                      </span>
                    )}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  {hasData ? (
                    <span
                      className="tabular-nums inline-block rounded px-2 py-0.5 text-sm font-semibold"
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
                  ) : (
                    <span style={{ color: "var(--color-text-muted)" }}>—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {city.profit_absolute !== null ? (
                    <div className="relative flex items-center justify-end">
                      {profitBarWidth > 0 && (
                        <div
                          className="absolute inset-y-0 right-0 rounded-sm opacity-15"
                          style={{
                            width: `${profitBarWidth}%`,
                            background: "var(--color-profit-strong)",
                          }}
                        />
                      )}
                      <span
                        className="tabular-nums relative z-10 text-sm font-medium"
                        style={{
                          fontFamily: "var(--font-plex-mono), monospace",
                          color: city.profit_absolute >= 0
                            ? "var(--color-profit-strong)"
                            : "var(--color-loss-strong)",
                        }}
                      >
                        {formatSilver(city.profit_absolute)}
                      </span>
                    </div>
                  ) : (
                    <span style={{ color: "var(--color-text-muted)" }}>—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
