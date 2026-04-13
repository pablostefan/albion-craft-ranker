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

  return (
    <div className="space-y-6">
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
          <tfoot>
            <tr style={{ borderTop: "2px solid var(--color-border-strong)" }}>
              <td colSpan={3} className="px-4 py-2 text-right text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>
                Custo Bruto de Materiais
              </td>
              <td
                className="tabular-nums px-4 py-2 text-right text-sm font-semibold"
                style={{ fontFamily: "var(--font-plex-mono), monospace" }}
              >
                {formatSilver(grossMaterialCost)}
              </td>
              <td className="hidden sm:table-cell" />
              <td className="hidden sm:table-cell" />
            </tr>
            <tr>
              <td colSpan={3} className="px-4 py-2 text-right text-xs font-semibold" style={{ color: "var(--color-profit-strong)" }}>
                Economia RRR
              </td>
              <td
                className="tabular-nums px-4 py-2 text-right text-sm font-semibold"
                style={{ fontFamily: "var(--font-plex-mono), monospace", color: "var(--color-profit-strong)" }}
              >
                -{formatSilver(rrrSavings)}
              </td>
              <td className="hidden sm:table-cell" />
              <td className="hidden sm:table-cell" />
            </tr>
            <tr style={{ borderTop: "1px solid var(--color-border-default)" }}>
              <td colSpan={3} className="px-4 py-2 text-right text-xs font-bold" style={{ color: "var(--color-text-primary)" }}>
                Custo Efetivo de Craft
              </td>
              <td
                className="tabular-nums px-4 py-2 text-right text-sm font-bold"
                style={{ fontFamily: "var(--font-plex-mono), monospace", color: "var(--color-accent-gold)" }}
              >
                {formatSilver(item.effective_craft_cost)}
              </td>
              <td className="hidden sm:table-cell" />
              <td className="hidden sm:table-cell" />
            </tr>
            {optimizedMaterialCost != null && (
              <>
                <tr>
                  <td colSpan={6} className="px-4 py-0">
                    <div style={{ borderTop: "1px dashed var(--color-border-default)" }} />
                  </td>
                </tr>
                <tr>
                  <td colSpan={3} className="px-4 py-2 text-right text-xs font-semibold" style={{ color: "var(--color-info)" }}>
                    Custo Otimizado (melhor cidade)
                  </td>
                  <td
                    className="tabular-nums px-4 py-2 text-right text-sm font-semibold"
                    style={{ fontFamily: "var(--font-plex-mono), monospace", color: "var(--color-info)" }}
                  >
                    {formatSilver(optimizedMaterialCost)}
                  </td>
                  <td className="hidden sm:table-cell" />
                  <td className="hidden sm:table-cell" />
                </tr>
                {optimizedProfit != null && (
                  <tr>
                    <td colSpan={3} className="px-4 py-2 text-right text-xs font-bold" style={{ color: "var(--color-text-primary)" }}>
                      Lucro Otimizado
                    </td>
                    <td
                      className="tabular-nums px-4 py-2 text-right text-sm font-bold"
                      style={{
                        fontFamily: "var(--font-plex-mono), monospace",
                        color: optimizedProfit >= 0
                          ? "var(--color-profit-strong)"
                          : "var(--color-loss-strong)",
                      }}
                    >
                      {formatSilver(optimizedProfit)}
                    </td>
                    <td className="hidden sm:table-cell" />
                    <td className="hidden sm:table-cell" />
                  </tr>
                )}
                {optimizedProfit != null && (optimizedProfit - item.profit_absolute) > 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-2 text-right text-xs font-semibold" style={{ color: "var(--color-profit-strong)" }}>
                      Economia Potencial
                    </td>
                    <td
                      className="tabular-nums px-4 py-2 text-right text-sm font-semibold"
                      style={{ fontFamily: "var(--font-plex-mono), monospace", color: "var(--color-profit-strong)" }}
                    >
                      +{formatSilver(optimizedProfit - item.profit_absolute)}
                    </td>
                    <td className="hidden sm:table-cell" />
                    <td className="hidden sm:table-cell" />
                  </tr>
                )}
              </>
            )}
          </tfoot>
        </table>
      </div>

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
          <div
            className="my-2 border-t"
            style={{ borderColor: "var(--color-border-default)" }}
          />
          <RevenueRow label="Receita Líquida" value={item.net_revenue} bold />
          <RevenueRow label="− Custo Efetivo de Craft" value={-item.effective_craft_cost} muted />
          <div
            className="my-2 border-t"
            style={{ borderColor: "var(--color-border-strong)" }}
          />
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold" style={{ color: "var(--color-text-primary)" }}>
              Lucro Final
            </span>
            <span
              className="tabular-nums text-lg font-bold"
              style={{
                fontFamily: "var(--font-plex-mono), monospace",
                color: item.profit_absolute >= 0
                  ? "var(--color-profit-strong)"
                  : "var(--color-loss-strong)",
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
