"use client";

import type { MaterialCost, ScoredItem } from "@/lib/types";
import { formatSilver, itemIconUrl } from "@/lib/format";

interface CostBreakdownProps {
  materials: MaterialCost[];
  item: ScoredItem;
  optimizedMaterialCost?: number | null;
  optimizedProfit?: number | null;
}

function extractMaterialName(itemId: string): string {
  return itemId
    .replace(/^T\d+_/, "")
    .replace(/@\d+$/, "")
    .replace(/_/g, " ");
}

export default function CostBreakdown({ materials, item, optimizedMaterialCost, optimizedProfit }: CostBreakdownProps) {
  const grossMaterialCost = materials.reduce((sum, m) => sum + m.total_price, 0);
  const rrrSavings = grossMaterialCost - item.effective_craft_cost;
  const potentialSavings = optimizedProfit != null ? optimizedProfit - item.profit_absolute : 0;

  return (
    <div className="space-y-4">
      {/* ── Materials Table ── */}
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
              <th scope="col" className="px-4 py-3 text-left text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>Material</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>Qtd</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>Preço Unit.</th>
              <th scope="col" className="px-4 py-3 text-right text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>Subtotal</th>
              <th scope="col" className="hidden px-4 py-3 text-center text-xs font-semibold sm:table-cell" style={{ color: "var(--color-text-secondary)" }}>RRR Aplicado</th>
              <th scope="col" className="hidden px-4 py-3 text-center text-xs font-semibold sm:table-cell" style={{ color: "var(--color-text-secondary)" }}>Melhor Cidade</th>
            </tr>
          </thead>
          <tbody>
            {materials.map((mat) => {
              const isArtifact = mat.is_artifact_component;
              return (
                <tr
                  key={mat.item_id}
                  style={{
                    borderBottom: "1px solid var(--color-border-muted)",
                    borderLeft: isArtifact ? "3px solid var(--color-accent-gold)" : "3px solid transparent",
                  }}
                >
                  <td className="px-4 py-3 text-sm">
                    <span className="flex items-center gap-2">
                      <img
                        src={itemIconUrl(mat.item_id, 40)}
                        alt={extractMaterialName(mat.item_id)}
                        width={28}
                        height={28}
                        className="shrink-0 rounded"
                        loading="lazy"
                      />
                      {extractMaterialName(mat.item_id)}
                      {isArtifact && (
                        <span
                          className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
                          style={{
                            background: "var(--color-bg-overlay)",
                            color: "var(--color-accent-gold)",
                            border: "1px solid var(--color-accent-gold)",
                          }}
                        >
                          Artefato
                        </span>
                      )}
                    </span>
                  </td>
                  <td
                    className="tabular-nums px-4 py-3 text-right text-sm"
                    style={{ fontFamily: "var(--font-plex-mono), monospace" }}
                  >
                    {mat.quantity}
                  </td>
                  <td
                    className="tabular-nums px-4 py-3 text-right text-sm"
                    style={{ fontFamily: "var(--font-plex-mono), monospace", color: "var(--color-text-secondary)" }}
                  >
                    {formatSilver(mat.unit_price)}
                  </td>
                  <td
                    className="tabular-nums px-4 py-3 text-right text-sm"
                    style={{ fontFamily: "var(--font-plex-mono), monospace" }}
                  >
                    {formatSilver(mat.total_price)}
                  </td>
                  <td className="hidden px-4 py-3 text-center text-xs sm:table-cell">
                    {isArtifact ? (
                      <span
                        className="rounded px-2 py-0.5 text-xs font-medium"
                        style={{
                          background: "var(--color-bg-overlay)",
                          color: "var(--color-accent-gold)",
                        }}
                      >
                        Sem RRR
                      </span>
                    ) : (
                      <span style={{ color: "var(--color-profit-strong)" }}>
                        RRR aplicado
                      </span>
                    )}
                  </td>
                  <td className="hidden px-4 py-3 text-center text-xs sm:table-cell">
                    {mat.best_buy_city ? (
                      <span
                        style={{
                          color: mat.best_buy_city !== item.craft_city
                            ? "var(--color-profit-strong)"
                            : "var(--color-text-muted)",
                        }}
                      >
                        {mat.best_buy_city}
                        {mat.best_buy_price != null && mat.best_buy_price !== mat.unit_price && (
                          <span
                            className="block text-[10px]"
                            style={{ color: "var(--color-text-muted)" }}
                          >
                            ({formatSilver(mat.best_buy_price)})
                          </span>
                        )}
                      </span>
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

      {/* ── Cost Summary Cards ── */}
      <div className="grid gap-3 sm:grid-cols-3">
        {/* Card: Custo Bruto */}
        <CostCard
          label="Custo Bruto"
          sublabel="soma dos materiais"
          value={formatSilver(grossMaterialCost)}
          accentColor="var(--color-text-secondary)"
          borderColor="var(--color-border-default)"
        />
        {/* Card: Desconto RRR */}
        <CostCard
          label="Desconto RRR"
          sublabel="retorno de recursos"
          value={`-${formatSilver(rrrSavings)}`}
          accentColor="var(--color-profit-strong)"
          borderColor="var(--color-profit-strong)"
          highlight
        />
        {/* Card: Custo Efetivo — destaque principal */}
        <CostCard
          label="Custo Efetivo de Craft"
          sublabel="o que você paga de fato"
          value={formatSilver(item.effective_craft_cost)}
          accentColor="var(--color-accent-gold)"
          borderColor="var(--color-accent-gold)"
          prominent
        />
      </div>

      {/* ── Optimized Section (se disponível) ── */}
      {optimizedMaterialCost != null && (
        <div
          className="rounded-lg border overflow-hidden"
          style={{ borderColor: "var(--color-info)", background: "var(--color-bg-elevated)" }}
        >
          {/* Header */}
          <div
            className="flex items-center gap-2 px-4 py-2.5"
            style={{
              background: "color-mix(in srgb, var(--color-info) 12%, var(--color-bg-panel))",
              borderBottom: "1px solid color-mix(in srgb, var(--color-info) 30%, transparent)",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M8 1l2 5h5l-4 3 2 5-5-3-5 3 2-5-4-3h5z" fill="var(--color-info)" opacity="0.9" />
            </svg>
            <span
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: "var(--color-info)" }}
            >
              Cenário Otimizado — comprando na melhor cidade
            </span>
          </div>

          <div className="grid gap-0 sm:grid-cols-3">
            {/* Custo Otimizado */}
            <div
              className="flex flex-col justify-between gap-1 px-4 py-3"
              style={{ borderRight: "1px solid var(--color-border-muted)" }}
            >
              <span className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
                Custo Otimizado
              </span>
              <span
                className="tabular-nums text-lg font-bold"
                style={{ fontFamily: "var(--font-plex-mono), monospace", color: "var(--color-info)" }}
              >
                {formatSilver(optimizedMaterialCost)}
              </span>
              <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                comprando materiais fora
              </span>
            </div>

            {/* Lucro Otimizado */}
            {optimizedProfit != null && (
              <div
                className="flex flex-col justify-between gap-1 px-4 py-3"
                style={{ borderRight: "1px solid var(--color-border-muted)" }}
              >
                <span className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
                  Lucro Otimizado
                </span>
                <span
                  className="tabular-nums text-lg font-bold"
                  style={{
                    fontFamily: "var(--font-plex-mono), monospace",
                    color: optimizedProfit >= 0 ? "var(--color-profit-strong)" : "var(--color-loss-strong)",
                  }}
                >
                  {formatSilver(optimizedProfit)}
                </span>
                <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                  com custo de cidade ótima
                </span>
              </div>
            )}

            {/* Economia Potencial */}
            {optimizedProfit != null && potentialSavings > 0 && (
              <div className="flex flex-col justify-between gap-1 px-4 py-3">
                <span className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
                  Economia Potencial
                </span>
                <span
                  className="tabular-nums text-lg font-bold"
                  style={{ fontFamily: "var(--font-plex-mono), monospace", color: "var(--color-profit-strong)" }}
                >
                  +{formatSilver(potentialSavings)}
                </span>
                <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                  vs custo atual de craft
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Revenue Breakdown ── */}
      <div
        className="rounded-lg border p-4"
        style={{
          background: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-default)",
        }}
      >
        <h3
          className="mb-3 text-sm font-bold tracking-wide"
          style={{ fontFamily: "var(--font-cinzel), Cinzel, serif", color: "var(--color-text-secondary)" }}
        >
          Receita
        </h3>
        <div className="space-y-2">
          <RevenueRow label="Preço de Venda" value={item.sell_price} />
          <RevenueRow label="Taxa de Setup (2.5%)" value={-item.setup_fee} muted />
          <RevenueRow label="Imposto de Venda" value={-item.sales_tax} muted />
          <div className="my-2 border-t" style={{ borderColor: "var(--color-border-default)" }} />
          <RevenueRow label="Receita Líquida" value={item.net_revenue} bold />
          <RevenueRow label="− Custo Efetivo de Craft" value={-item.effective_craft_cost} muted />
          <div className="my-2 border-t" style={{ borderColor: "var(--color-border-strong)" }} />
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold" style={{ color: "var(--color-text-primary)" }}>Lucro Final</span>
            <span
              className="tabular-nums text-lg font-bold"
              style={{
                fontFamily: "var(--font-plex-mono), monospace",
                color: item.profit_absolute >= 0 ? "var(--color-profit-strong)" : "var(--color-loss-strong)",
              }}
            >
              {formatSilver(item.profit_absolute)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function CostCard({
  label,
  sublabel,
  value,
  accentColor,
  borderColor,
  highlight,
  prominent,
}: {
  label: string;
  sublabel: string;
  value: string;
  accentColor: string;
  borderColor: string;
  highlight?: boolean;
  prominent?: boolean;
}) {
  return (
    <div
      className="flex flex-col gap-1.5 rounded-lg border px-4 py-3"
      style={{
        background: highlight || prominent
          ? `color-mix(in srgb, ${accentColor} 8%, var(--color-bg-elevated))`
          : "var(--color-bg-elevated)",
        borderColor,
        borderLeftWidth: prominent ? "3px" : "1px",
      }}
    >
      <span
        className="text-xs font-semibold uppercase tracking-wide"
        style={{ color: accentColor }}
      >
        {label}
      </span>
      <span
        className={`tabular-nums font-bold ${prominent ? "text-2xl" : "text-xl"}`}
        style={{ fontFamily: "var(--font-plex-mono), monospace", color: accentColor }}
      >
        {value}
      </span>
      <span className="text-[11px]" style={{ color: "var(--color-text-muted)" }}>
        {sublabel}
      </span>
    </div>
  );
}

function RevenueRow({
  label,
  value,
  muted,
  bold,
}: {
  label: string;
  value: number;
  muted?: boolean;
  bold?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span
        className={`text-sm ${bold ? "font-semibold" : ""}`}
        style={{ color: muted ? "var(--color-text-muted)" : "var(--color-text-secondary)" }}
      >
        {label}
      </span>
      <span
        className={`tabular-nums text-sm ${bold ? "font-semibold" : ""}`}
        style={{
          fontFamily: "var(--font-plex-mono), monospace",
          color: muted ? "var(--color-text-muted)" : "var(--color-text-primary)",
        }}
      >
        {formatSilver(value)}
      </span>
    </div>
  );
}
