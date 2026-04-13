"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import type { ScoredItem, SortField, SortOrder } from "@/lib/types";
import { formatPct, formatSilver, extractItemName, extractTier, extractEnchantment, itemIconUrl } from "@/lib/format";

/* ── Sort indicator ── */

function SortArrow({ field, currentSort, currentOrder }: {
  field: SortField;
  currentSort: SortField;
  currentOrder: SortOrder;
}) {
  if (field !== currentSort) {
    return <span className="ml-1 opacity-30">↕</span>;
  }
  return (
    <span className="ml-1" style={{ color: "var(--color-accent-gold)" }}>
      {currentOrder === "desc" ? "↓" : "↑"}
    </span>
  );
}

/* ── Skeleton rows ── */

function SkeletonRow({ index }: { index: number }) {
  return (
    <tr key={index}>
      <td className="px-3 py-3"><div className="skeleton h-4 w-6" /></td>
      <td className="px-3 py-3"><div className="skeleton h-4 w-32" /></td>
      <td className="px-3 py-3"><div className="skeleton h-4 w-8" /></td>
      <td className="hidden px-3 py-3 md:table-cell"><div className="skeleton h-4 w-8" /></td>
      <td className="px-3 py-3"><div className="skeleton h-6 w-20" /></td>
      <td className="px-3 py-3"><div className="skeleton h-4 w-16" /></td>
      <td className="hidden px-3 py-3 md:table-cell"><div className="skeleton h-4 w-14" /></td>
      <td className="hidden px-3 py-3 lg:table-cell"><div className="skeleton h-4 w-10" /></td>
      <td className="hidden px-3 py-3 lg:table-cell"><div className="skeleton h-4 w-10" /></td>
    </tr>
  );
}

/* ── Main component ── */

interface RankingTableProps {
  items: ScoredItem[];
  total: number;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  offset: number;
  limit: number;
}

const SORTABLE_COLUMNS: { field: SortField; label: string }[] = [
  { field: "final_score", label: "Lucro + Volume" },
  { field: "return_rate_pct", label: "Retorno %" },
  { field: "profit", label: "Lucro" },
  { field: "profit_per_focus", label: "Lucro/Foco" },
  { field: "daily_volume", label: "Vendas/dia (7d)" },
];

export default function RankingTable({
  items,
  total,
  loading,
  error,
  onRetry,
  offset,
  limit,
}: RankingTableProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentSort = (searchParams.get("sort_by") as SortField) || "daily_volume";
  const currentOrder = (searchParams.get("order") as SortOrder) || "desc";

  const updateParams = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(updates)) {
        if (v) params.set(k, v);
        else params.delete(k);
      }
      router.push(`?${params.toString()}`);
    },
    [router, searchParams],
  );

  const handleSort = useCallback(
    (field: SortField) => {
      const newOrder =
        field === currentSort && currentOrder === "desc" ? "asc" : "desc";
      updateParams({ sort_by: field, order: newOrder, offset: "0" });
    },
    [currentSort, currentOrder, updateParams],
  );

  const handlePageChange = useCallback(
    (newOffset: number) => {
      updateParams({ offset: String(Math.max(0, newOffset)) });
    },
    [updateParams],
  );

  const navigateToItem = useCallback(
    (productId: string) => {
      const params = new URLSearchParams(searchParams.toString());
      router.push(`/items/${encodeURIComponent(productId)}?${params.toString()}`);
    },
    [router, searchParams],
  );

  /* ── Error state ── */
  if (error && !loading && items.length === 0) {
    return (
      <div
        className="rounded-lg border p-6 text-center"
        style={{
          background: "var(--color-loss-soft)",
          borderColor: "var(--color-loss-strong)",
        }}
      >
        <p className="mb-3 text-sm" style={{ color: "var(--color-loss-strong)" }}>
          Erro ao carregar dados do ranking
        </p>
        <p className="mb-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
          {error}
        </p>
        <button
          onClick={onRetry}
          className="rounded px-4 py-2 text-sm font-medium transition-colors"
          style={{
            background: "var(--color-bg-overlay)",
            color: "var(--color-text-primary)",
            border: "1px solid var(--color-border-default)",
          }}
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  return (
    <div>
      {/* Stale / error banner */}
      {error && items.length > 0 && (
        <div
          className="mb-3 rounded border px-4 py-2 text-xs"
          style={{
            background: "var(--color-info-soft)",
            borderColor: "var(--color-warning-strong)",
            color: "var(--color-warning-strong)",
          }}
        >
          Dados podem estar desatualizados — {error}{" "}
          <button onClick={onRetry} className="underline">
            Tentar novamente
          </button>
        </div>
      )}

      {/* Table wrapper */}
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
              <th scope="col" className="sticky left-0 z-10 px-3 py-3 text-left text-xs font-semibold" style={{ background: "var(--color-bg-panel)", color: "var(--color-text-secondary)" }}>
                #
              </th>
              <th scope="col" className="px-3 py-3 text-left text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>
                Item
              </th>
              <th scope="col" className="px-3 py-3 text-left text-xs font-semibold" style={{ color: "var(--color-text-secondary)" }}>
                Tier
              </th>
              <th scope="col" className="hidden px-3 py-3 text-left text-xs font-semibold md:table-cell" style={{ color: "var(--color-text-secondary)" }}>
                Enc
              </th>
              {SORTABLE_COLUMNS.map((col) => (
                <th
                  scope="col"
                  key={col.field}
                  className={`cursor-pointer select-none px-3 py-3 text-left text-xs font-semibold transition-colors hover:text-[var(--color-accent-gold)] ${col.field === "profit_per_focus" ? "hidden md:table-cell" : col.field === "daily_volume" ? "hidden lg:table-cell" : ""}`}
                  style={{ color: "var(--color-text-secondary)" }}
                  onClick={() => handleSort(col.field)}
                  role="columnheader"
                  aria-sort={
                    col.field === currentSort
                      ? currentOrder === "desc"
                        ? "descending"
                        : "ascending"
                      : "none"
                  }
                >
                  {col.label}
                  <SortArrow field={col.field} currentSort={currentSort} currentOrder={currentOrder} />
                </th>
              ))}
              <th scope="col" className="hidden px-3 py-3 text-left text-xs font-semibold lg:table-cell" style={{ color: "var(--color-text-secondary)" }}>
                Atualização
              </th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0
              ? Array.from({ length: 8 }, (_, i) => <SkeletonRow key={i} index={i} />)
              : items.map((item, idx) => (
                  <ItemRow
                    key={item.product_id}
                    item={item}
                    rank={offset + idx + 1}
                    onClick={() => navigateToItem(item.product_id)}
                  />
                ))}
          </tbody>
        </table>

        {/* Empty state */}
        {!loading && items.length === 0 && !error && (
          <div className="px-6 py-12 text-center">
            <p className="mb-2 text-sm" style={{ color: "var(--color-text-secondary)" }}>
              Nenhum item encontrado com os filtros atuais
            </p>
            <button
              onClick={() => router.push("/")}
              className="text-xs underline"
              style={{ color: "var(--color-info)" }}
            >
              Limpar todos os filtros
            </button>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="mt-4 flex items-center justify-between text-xs" style={{ color: "var(--color-text-muted)" }}>
          <span>
            Mostrando {offset + 1}–{Math.min(offset + limit, total)} de{" "}
            {total.toLocaleString()} itens
          </span>
          <div className="flex gap-2">
            <button
              disabled={offset === 0}
              onClick={() => handlePageChange(offset - limit)}
              className="rounded border px-3 py-1.5 transition-colors disabled:opacity-30"
              style={{
                background: "var(--color-bg-overlay)",
                borderColor: "var(--color-border-default)",
                color: "var(--color-text-primary)",
              }}
            >
              ← Anterior
            </button>
            <span className="flex items-center px-2" style={{ color: "var(--color-text-secondary)" }}>
              Página {currentPage} / {totalPages}
            </span>
            <button
              disabled={offset + limit >= total}
              onClick={() => handlePageChange(offset + limit)}
              className="rounded border px-3 py-1.5 transition-colors disabled:opacity-30"
              style={{
                background: "var(--color-bg-overlay)",
                borderColor: "var(--color-border-default)",
                color: "var(--color-text-primary)",
              }}
            >
              Próximo →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Item row ── */

function ItemRow({
  item,
  rank,
  onClick,
}: {
  item: ScoredItem;
  rank: number;
  onClick: () => void;
}) {
  const isPositive = item.return_rate_pct > 0.5;
  const isNegative = item.return_rate_pct < -0.5;

  const borderColor = isPositive
    ? "var(--color-profit-strong)"
    : isNegative
      ? "var(--color-loss-strong)"
      : "transparent";

  return (
    <tr
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(); } }}
      tabIndex={0}
      role="link"
      className="group cursor-pointer transition-colors"
      style={{
        borderBottom: "1px solid var(--color-border-muted)",
        borderLeft: `3px solid ${borderColor}`,
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.background = "var(--color-bg-overlay)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.background = "";
      }}
    >
      {/* Rank */}
      <td
        className="sticky left-0 z-10 px-3 py-3 text-xs font-medium"
        style={{ background: "inherit", color: "var(--color-text-muted)" }}
      >
        {rank}
      </td>

      {/* Item name */}
      <td className="max-w-[250px] px-3 py-3 text-sm font-medium">
        <div className="flex items-center gap-2">
          <img
            src={itemIconUrl(item.product_id, 40)}
            alt={extractItemName(item.product_id)}
            width={32}
            height={32}
            className="shrink-0 rounded"
            loading="lazy"
            style={{ imageRendering: "auto" }}
          />
          <span className="truncate">{extractItemName(item.product_id)}</span>
        </div>
      </td>

      {/* Tier */}
      <td className="px-3 py-3 text-xs font-semibold" style={{ color: "var(--color-accent-gold)" }}>
        {extractTier(item.product_id)}
      </td>

      {/* Enchantment */}
      <td className="hidden px-3 py-3 text-xs md:table-cell" style={{ color: "var(--color-accent-gold)" }}>
        {(() => {
          const enchStr = extractEnchantment(item.product_id);
          const enchLevel = parseInt(enchStr.replace("@", ""));
          const stars = "★".repeat(enchLevel) + "☆".repeat(Math.max(0, 4 - enchLevel));
          return <span>{stars}</span>;
        })()}
      </td>

      {/* Final score (Lucro + Volume) */}
      <td className="px-3 py-3">
        <span
          className="tabular-nums inline-block rounded px-2 py-0.5 text-base font-bold md:text-lg"
          style={{
            fontFamily: "var(--font-plex-mono), IBM Plex Mono, Menlo, monospace",
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
          {(item.final_score * 100).toFixed(1)}
        </span>
      </td>

      {/* Return rate */}
      <td className="px-3 py-3">
        <span
          className="tabular-nums inline-block rounded px-2 py-0.5 text-base font-bold md:text-lg"
          style={{
            fontFamily: "var(--font-plex-mono), IBM Plex Mono, Menlo, monospace",
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
          aria-label={
            isNegative
              ? `negative return rate ${item.return_rate_pct.toFixed(1)} percent`
              : `${item.return_rate_pct.toFixed(1)} percent return rate`
          }
        >
          {formatPct(item.return_rate_pct)}
        </span>
      </td>

      {/* Profit */}
      <td
        className="tabular-nums px-3 py-3 text-sm"
        style={{
          fontFamily: "var(--font-plex-mono), IBM Plex Mono, Menlo, monospace",
          color: item.profit_absolute >= 0
            ? "var(--color-profit-strong)"
            : "var(--color-loss-strong)",
        }}
      >
        {formatSilver(item.profit_absolute)}
      </td>

      {/* Profit per focus */}
      <td
        className="tabular-nums hidden px-3 py-3 text-xs md:table-cell"
        style={{
          fontFamily: "var(--font-plex-mono), IBM Plex Mono, Menlo, monospace",
          color: "var(--color-text-secondary)",
        }}
      >
        {item.focus_cost > 0 ? formatSilver(item.profit_per_focus) : "—"}
      </td>

      {/* Daily Volume */}
      <td className="hidden px-3 py-3 text-right tabular-nums lg:table-cell">
        {item.daily_volume != null
          ? Math.round(item.daily_volume).toLocaleString("pt-BR")
          : "—"}
      </td>

      {/* Freshness */}
      <td className="hidden px-3 py-3 lg:table-cell">
        <FreshnessBadge score={item.freshness_score} />
      </td>
    </tr>
  );
}

/* ── Badge components ── */

function FreshnessBadge({ score }: { score: number }) {
  const label = score >= 0.7 ? "Recente" : score >= 0.4 ? "OK" : "Antigo";
  const color =
    score >= 0.7
      ? "var(--color-info)"
      : score >= 0.4
        ? "var(--color-warning-strong)"
        : "var(--color-loss-strong)";
  return (
    <span
      className="rounded px-1.5 py-0.5 text-xs font-medium"
      style={{
        color,
        background: "var(--color-bg-overlay)",
        border: `1px solid ${color}33`,
      }}
    >
      {label}
    </span>
  );
}
