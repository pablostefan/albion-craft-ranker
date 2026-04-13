"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import type { ItemDetailResponse } from "@/lib/types";
import { fetchItemDetail } from "@/lib/api";
import {
  formatPct,
  formatSilver,
  extractItemName,
  extractTier,
  extractEnchantment,
  itemIconUrl,
} from "@/lib/format";
import CostBreakdown from "@/components/CostBreakdown";
import CityComparisonTable from "@/components/CityComparison";
import { useFavorites } from "@/lib/favorites";

export default function ItemDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  const productId = decodeURIComponent(params.id);
  const { isFavorite, toggleFavorite } = useFavorites();
  const favorited = isFavorite(productId);
  const city = searchParams.get("city") ?? undefined;
  const market = searchParams.get("market") ?? undefined;
  const sellCity = searchParams.get("sell_city") ?? undefined;
  const excludeCities = searchParams.get("exclude_caerleon") !== "false" ? "Caerleon" : undefined;
  const useFocus = searchParams.get("use_focus") === "true" ? true : undefined;

  const [data, setData] = useState<ItemDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchItemDetail(productId, { city, market, sell_city: sellCity, exclude_cities: excludeCities, use_focus: useFocus })
      .then((res) => { if (!cancelled) { setData(res); setError(null); } })
      .catch((err: Error) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [productId, city, market, sellCity, excludeCities, useFocus]);

  // loadData kept only for retry button
  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchItemDetail(productId, { city, market, sell_city: sellCity, exclude_cities: excludeCities, use_focus: useFocus })
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [productId, city, market, sellCity, excludeCities, useFocus]);

  const backHref = `/?${searchParams.toString()}`;
  const itemName = extractItemName(productId);
  const tier = extractTier(productId);
  const enchantment = extractEnchantment(productId);

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <BackLink href={backHref} />
        <div className="space-y-4">
          <div className="skeleton h-8 w-64" />
          <div className="skeleton h-6 w-48" />
          <div className="skeleton h-32 w-full rounded-lg" />
          <div className="skeleton h-48 w-full rounded-lg" />
          <div className="skeleton h-40 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  /* ── Error state ── */
  if (error || !data) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <BackLink href={backHref} />
        <div
          className="rounded-lg border p-6 text-center"
          style={{
            background: "var(--color-loss-soft)",
            borderColor: "var(--color-loss-strong)",
          }}
        >
          <p className="mb-3 text-sm" style={{ color: "var(--color-loss-strong)" }}>
            Erro ao carregar detalhes do item
          </p>
          <p className="mb-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
            {error ?? "Erro desconhecido"}
          </p>
          <button
            onClick={loadData}
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
      </div>
    );
  }

  const { item, cost_breakdown, city_comparison, optimized_material_cost, optimized_profit, daily_volume } = data;
  const isPositive = item.return_rate_pct > 0.5;
  const isNegative = item.return_rate_pct < -0.5;

  return (
    <div className="mx-auto max-w-4xl space-y-8 pb-12">
      {/* ── A) Header / Overview ── */}
      <div>
        <BackLink href={backHref} />

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <img
            src={itemIconUrl(productId, 128)}
            alt={itemName}
            width={64}
            height={64}
            className="shrink-0 rounded"
            style={{ imageRendering: "auto" }}
          />
          <h1
            className="text-2xl font-bold tracking-wide md:text-3xl"
            style={{
              fontFamily: "var(--font-cinzel), Cinzel, serif",
              color: "var(--color-text-primary)",
            }}
          >
            {itemName}
          </h1>
          <span
            className="rounded px-2 py-0.5 text-xs font-bold"
            style={{
              background: "var(--color-bg-overlay)",
              color: "var(--color-accent-gold)",
              border: "1px solid var(--color-accent-gold)",
            }}
          >
            {tier}
          </span>
          {enchantment !== "@0" && (
            <span
              className="rounded px-2 py-0.5 text-xs font-bold"
              style={{
                background: "var(--color-bg-overlay)",
                color: "var(--color-accent-ember)",
                border: "1px solid var(--color-accent-ember)",
              }}
            >
              {enchantment}
            </span>
          )}
          <button
            onClick={() => toggleFavorite(productId)}
            className="ml-1 text-2xl leading-none transition-transform hover:scale-125"
            style={{ color: favorited ? "var(--color-accent-gold)" : "var(--color-text-muted)" }}
            aria-label={favorited ? "Remover dos favoritos" : "Adicionar aos favoritos"}
          >
            {favorited ? "★" : "☆"}
          </button>
        </div>

        <div
          className="mt-2 flex flex-wrap gap-4 text-xs"
          style={{ color: "var(--color-text-muted)" }}
        >
          <span>
            Craftar em <strong style={{ color: "var(--color-text-secondary)" }}>{item.craft_city}</strong>
          </span>
          <span>
            Vender via <strong style={{ color: "var(--color-text-secondary)" }}>{item.sell_mode}</strong>
          </span>
          <FreshnessBadge score={item.freshness_score} />
        </div>
      </div>

      {/* ── B) Profit Summary (HERO) ── */}
      <section
        className="rounded-lg border p-6"
        style={{
          background: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-default)",
        }}
      >
        <h2
          className="mb-4 text-sm font-bold uppercase tracking-wider"
          style={{
            fontFamily: "var(--font-cinzel), Cinzel, serif",
            color: "var(--color-text-secondary)",
          }}
        >
          Resumo de Lucro
        </h2>

        <div className="flex flex-col items-center gap-2 text-center sm:items-start sm:text-left">
          <span
            className="tabular-nums rounded-lg px-4 py-2 text-3xl font-extrabold md:text-4xl"
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
            aria-label={`Return rate: ${item.return_rate_pct.toFixed(1)} percent`}
          >
            {formatPct(item.return_rate_pct)}
          </span>
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
            Lucro líquido como porcentagem do custo total de craft
          </p>
        </div>

        <div
          className="mt-4 grid gap-4 sm:grid-cols-3"
        >
          <MetricCard label="Lucro" value={formatSilver(item.profit_absolute)} positive={item.profit_absolute >= 0} />
          {item.focus_cost > 0 && (
            <MetricCard label="Lucro / Foco" value={formatSilver(item.profit_per_focus)} positive={item.profit_per_focus >= 0} />
          )}
          {item.focus_cost > 0 && (
            <MetricCard label="Custo de Foco" value={formatSilver(item.focus_cost)} />
          )}
        </div>
      </section>

      {/* ── B2) Volume de Vendas ── */}
      {(() => {
        const volColor = item.volume_norm >= 0.7
          ? "var(--color-profit-strong)"
          : item.volume_norm >= 0.4
            ? "var(--color-accent-gold)"
            : "var(--color-loss-strong)";
        const volBgColor = item.volume_norm >= 0.7
          ? "var(--color-profit-soft)"
          : item.volume_norm >= 0.4
            ? "var(--color-info-soft)"
            : "var(--color-loss-soft)";
        const volLabel = item.volume_norm >= 0.7 ? "Alta" : item.volume_norm >= 0.4 ? "Média" : "Baixa";
        const volPct = (item.volume_norm * 100).toFixed(0);

        return (
          <section
            className="rounded-lg border p-6"
            style={{
              background: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-default)",
            }}
          >
            {/* Header row */}
            <div className="mb-4 flex items-center justify-between">
              <h2
                className="text-sm font-bold uppercase tracking-wider"
                style={{
                  fontFamily: "var(--font-cinzel), Cinzel, serif",
                  color: "var(--color-text-secondary)",
                }}
              >
                Volume de Vendas
              </h2>
              <span
                className="rounded px-2 py-0.5 text-xs font-bold"
                style={{ background: volBgColor, color: volColor }}
              >
                {volLabel}
              </span>
            </div>

            {/* Progress bar */}
            <div className="mb-1 h-2 w-full overflow-hidden rounded-full" style={{ background: "var(--color-bg-overlay)" }}>
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${volPct}%`, background: volColor }}
              />
            </div>
            <p className="mb-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
              {volPct}% do ranking
            </p>

            {/* Key metrics grid */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div
                className="rounded-lg border p-4"
                style={{
                  background: "var(--color-bg-overlay)",
                  borderColor: "var(--color-border-default)",
                }}
              >
                <p className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
                  Volume Diário
                </p>
                <p
                  className="mt-1 tabular-nums text-lg font-extrabold"
                  style={{
                    fontFamily: "var(--font-plex-mono), monospace",
                    color: daily_volume != null && daily_volume > 0 ? volColor : "var(--color-text-muted)",
                  }}
                >
                  {daily_volume != null ? Math.round(daily_volume).toLocaleString("pt-BR") : "—"}
                </p>
                <p className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
                  Mediana de itens vendidos/dia (7d)
                </p>
              </div>
              <div
                className="rounded-lg border p-4"
                style={{
                  background: "var(--color-bg-overlay)",
                  borderColor: "var(--color-border-default)",
                }}
              >
                <p className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>
                  Peso no Ranking
                </p>
                <p
                  className="mt-1 tabular-nums text-lg font-extrabold"
                  style={{
                    fontFamily: "var(--font-plex-mono), monospace",
                    color: "var(--color-info)",
                  }}
                >
                  55%
                </p>
                <p className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
                  Contribuição do volume no score final
                </p>
              </div>
            </div>

            {/* Explanation */}
            <p className="mt-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
              O volume diário indica a mediana de itens efetivamente vendidos por dia nos últimos 7 dias.
            </p>
          </section>
        );
      })()}

      {/* ── C) Cost Breakdown ── */}
      <section>
        <h2
          className="mb-4 text-sm font-bold uppercase tracking-wider"
          style={{
            fontFamily: "var(--font-cinzel), Cinzel, serif",
            color: "var(--color-text-secondary)",
          }}
        >
          Detalhamento de Custo
        </h2>
        <CostBreakdown materials={cost_breakdown} item={item} optimizedMaterialCost={optimized_material_cost} optimizedProfit={optimized_profit} />
      </section>

      {/* ── D) City Comparison ── */}
      <section>
        <h2
          className="mb-4 text-sm font-bold uppercase tracking-wider"
          style={{
            fontFamily: "var(--font-cinzel), Cinzel, serif",
            color: "var(--color-text-secondary)",
          }}
        >
          Comparação por Cidade
        </h2>
        <CityComparisonTable cities={city_comparison} bestCity={item.best_city} />
      </section>

      {/* ── E) Black Market Comparison (conditional) ── */}
      {item.bm_sell_price !== null && (
        <section
          className="rounded-lg border p-4"
          style={{
            background: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-default)",
          }}
        >
          <h2
            className="mb-4 text-sm font-bold uppercase tracking-wider"
            style={{
              fontFamily: "var(--font-cinzel), Cinzel, serif",
              color: "var(--color-text-secondary)",
            }}
          >
            Mercado Negro
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Preço de Venda BM" value={formatSilver(item.bm_sell_price!)} />
            {item.bm_net_revenue !== null && (
              <MetricCard label="Receita Líquida BM" value={formatSilver(item.bm_net_revenue)} />
            )}
            {item.bm_profit !== null && (
              <MetricCard label="Lucro BM" value={formatSilver(item.bm_profit)} positive={item.bm_profit >= 0} />
            )}
            {item.bm_return_rate_pct !== null && (
              <MetricCard label="Retorno % BM" value={formatPct(item.bm_return_rate_pct)} positive={item.bm_return_rate_pct >= 0} />
            )}
          </div>
        </section>
      )}
    </div>
  );
}

/* ── Sub-components ── */

function BackLink({ href }: { href: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 rounded px-3 py-2 text-sm transition-colors"
      style={{
        color: "var(--color-text-secondary)",
        background: "var(--color-bg-overlay)",
        border: "1px solid var(--color-border-default)",
      }}
      aria-label="Voltar ao ranking"
    >
      <span aria-hidden="true">←</span>
      Voltar ao Ranking
    </Link>
  );
}

function MetricCard({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  const valueColor =
    positive === undefined
      ? "var(--color-text-primary)"
      : positive
        ? "var(--color-profit-strong)"
        : "var(--color-loss-strong)";

  return (
    <div
      className="rounded-lg border p-3"
      style={{
        background: "var(--color-bg-panel)",
        borderColor: "var(--color-border-muted)",
      }}
    >
      <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
        {label}
      </p>
      <p
        className="tabular-nums mt-1 text-lg font-bold"
        style={{
          fontFamily: "var(--font-plex-mono), monospace",
          color: valueColor,
        }}
      >
        {value}
      </p>
    </div>
  );
}

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
