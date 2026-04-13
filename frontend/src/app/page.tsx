"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import RankingTable from "@/components/RankingTable";
import FilterSidebar, {
  ActiveFilterChips,
  type FilterValues,
} from "@/components/FilterSidebar";
import { fetchItems, refreshPrices, ApiError } from "@/lib/api";
import { useFavorites } from "@/lib/favorites";
import type { ScoredItem, SortField, SortOrder, MarketMode } from "@/lib/types";

const DEFAULT_LIMIT = 25;

function useFilterValues(searchParams: URLSearchParams): FilterValues {
  return {
    market: (searchParams.get("market") as MarketMode) || "marketplace",
    category: searchParams.get("category") ?? "",
    tier: searchParams.get("tier") ?? "",
    enchantment: searchParams.get("enchantment") ?? "",
    city: searchParams.get("city") ?? "",
    quality: searchParams.get("quality") ?? "",
    minProfit: searchParams.get("min_profit") ?? "",
    w_profit: searchParams.get("w_profit") ?? "",
    w_focus: searchParams.get("w_focus") ?? "",
    w_volume: searchParams.get("w_volume") ?? "",
    w_freshness: searchParams.get("w_freshness") ?? "",
    excludeCaerleon: searchParams.get("exclude_caerleon") ?? "true",
    useFocus: searchParams.get("use_focus") ?? "false",
    nameSearch: searchParams.get("q") ?? "",
  };
}

function countActiveFilters(f: FilterValues): number {
  let n = 0;
  if (f.market !== "marketplace") n++;
  if (f.category) n++;
  if (f.tier) n++;
  if (f.enchantment) n++;
  if (f.city) n++;
  if (f.quality) n++;
  if (f.minProfit) n++;
  if (f.excludeCaerleon !== "true") n++;
  if (f.useFocus === "true") n++;
  if (f.nameSearch) n++;
  return n;
}

function useFavoritesOnly(searchParams: URLSearchParams) {
  return searchParams.get("favorites_only") === "true";
}

function RankingDashboard() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const sortBy = (searchParams.get("sort_by") as SortField) || "daily_volume";
  const order = (searchParams.get("order") as SortOrder) || "desc";
  const offset = Number(searchParams.get("offset") || "0");

  const filters = useFilterValues(searchParams);
  const activeFilterCount = countActiveFilters(filters);
  const showFavoritesOnly = useFavoritesOnly(searchParams);
  const { favorites, toggleFavorite } = useFavorites();

  const [items, setItems] = useState<ScoredItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const updateParam = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      // Reset pagination when filters change (unless changing offset itself)
      if (key !== "offset" && key !== "sort_by" && key !== "order") {
        params.delete("offset");
      }
      router.push(`?${params.toString()}`);
    },
    [router, searchParams],
  );

  const resetFilters = useCallback(() => {
    const params = new URLSearchParams();
    // Keep sort params only
    const sb = searchParams.get("sort_by");
    const ord = searchParams.get("order");
    if (sb) params.set("sort_by", sb);
    if (ord) params.set("order", ord);
    router.push(`?${params.toString()}`);
  }, [router, searchParams]);

  const removeFilter = useCallback(
    (key: string) => updateParam(key, ""),
    [updateParam],
  );

  const toggleFavoritesOnly = useCallback(() => {
    updateParam("favorites_only", showFavoritesOnly ? "" : "true");
  }, [updateParam, showFavoritesOnly]);

  const displayItems = showFavoritesOnly
    ? items.filter((i) => favorites.has(i.product_id))
    : items;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchItems({
        sort_by: sortBy,
        order,
        offset,
        limit: DEFAULT_LIMIT,
        market: filters.market !== "marketplace" ? filters.market : undefined,
        category: filters.category || undefined,
        tier: filters.tier ? Number(filters.tier) : undefined,
        enchantment: filters.enchantment ? Number(filters.enchantment) : undefined,
        city: filters.city || undefined,
        quality: filters.quality ? Number(filters.quality) : undefined,
        min_profit: filters.minProfit ? Number(filters.minProfit) : undefined,
        w_profit: filters.w_profit ? Number(filters.w_profit) : undefined,
        w_focus: filters.w_focus ? Number(filters.w_focus) : undefined,
        w_volume: filters.w_volume ? Number(filters.w_volume) : undefined,
        w_freshness: filters.w_freshness ? Number(filters.w_freshness) : undefined,
        exclude_cities: filters.excludeCaerleon === "true" ? "Caerleon" : undefined,
        use_focus: filters.useFocus === "true" ? true : undefined,
        name_search: filters.nameSearch || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `API error ${err.status}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Unknown error";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [sortBy, order, offset, filters.market, filters.category, filters.tier, filters.enchantment, filters.city, filters.quality, filters.minProfit, filters.w_profit, filters.w_focus, filters.w_volume, filters.w_freshness, filters.excludeCaerleon, filters.useFocus, filters.nameSearch]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refreshPrices();
      await load();
    } catch {
      // load() already handles its own error state
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex gap-6">
      {/* Sidebar */}
      <FilterSidebar
        filters={filters}
        onFilterChange={updateParam}
        onReset={resetFilters}
        activeFilterCount={activeFilterCount}
        showFavoritesOnly={showFavoritesOnly}
        onToggleFavoritesOnly={toggleFavoritesOnly}
        favoritesCount={favorites.size}
      />

      {/* Main content */}
      <div className="min-w-0 flex-1">
        {/* Summary strip */}
        <div
          className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border px-4 py-3"
          style={{
            background: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-default)",
          }}
        >
          <SummaryPill label="Total de Itens" value={total.toLocaleString()} />
          <SummaryPill
            label="Ordenado por"
            value={sortBy.replace(/_/g, " ")}
            accent
          />
          <SummaryPill
            label="Ordem"
            value={order === "desc" ? "Maior primeiro" : "Menor primeiro"}
          />
          {activeFilterCount > 0 && (
            <SummaryPill label="Filtros" value={String(activeFilterCount)} accent />
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="ml-auto rounded px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              background: refreshing ? "var(--color-bg-overlay)" : "var(--color-accent-gold)",
              color: refreshing ? "var(--color-text-muted)" : "var(--color-bg-base)",
              cursor: refreshing ? "not-allowed" : "pointer",
              opacity: refreshing ? 0.7 : 1,
            }}
          >
            {refreshing ? "Atualizando..." : "Atualizar Precos"}
          </button>
        </div>

        {/* Active filter chips */}
        <ActiveFilterChips filters={filters} onRemove={removeFilter} showFavoritesOnly={showFavoritesOnly} />

        <RankingTable
          items={displayItems}
          total={showFavoritesOnly ? displayItems.length : total}
          loading={loading}
          error={error}
          onRetry={load}
          offset={showFavoritesOnly ? 0 : offset}
          limit={showFavoritesOnly ? displayItems.length : DEFAULT_LIMIT}
          favorites={favorites}
          onToggleFavorite={toggleFavorite}
        />
      </div>
    </div>
  );
}

function SummaryPill({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="text-xs">
      <span style={{ color: "var(--color-text-muted)" }}>{label}: </span>
      <span
        className="font-medium"
        style={{ color: accent ? "var(--color-accent-gold)" : "var(--color-text-primary)" }}
      >
        {value}
      </span>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-20" style={{ color: "var(--color-text-muted)" }}>
          Loading...
        </div>
      }
    >
      <RankingDashboard />
    </Suspense>
  );
}
