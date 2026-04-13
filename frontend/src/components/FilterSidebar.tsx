"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import BlackMarketToggle from "@/components/BlackMarketToggle";
import WeightConfig from "@/components/WeightConfig";
import type { MarketMode, ConfigResponse } from "@/lib/types";
import { fetchConfig } from "@/lib/api";

/* ── Constants ── */

const CATEGORIES = [
  "armors",
  "artefacts",
  "bags",
  "capes",
  "consumables",
  "crafting",
  "farming",
  "furniture",
  "gathering",
  "head",
  "mounts",
  "offhands",
  "other",
  "shoes",
  "vanity",
  "weapons",
];

const CATEGORY_LABELS: Record<string, string> = {
  armors: "Armaduras",
  artefacts: "Artefatos",
  bags: "Bolsas",
  capes: "Capas",
  consumables: "Consumíveis",
  crafting: "Materiais",
  farming: "Fazenda",
  furniture: "Mobília",
  gathering: "Coleta",
  head: "Cabeça",
  mounts: "Montarias",
  offhands: "Off-hand",
  other: "Outros",
  shoes: "Calçados",
  vanity: "Vaidade",
  weapons: "Armas",
};

const TIERS = [4, 5, 6, 7, 8] as const;
const ENCHANTMENTS = [0, 1, 2, 3, 4] as const;

const CITIES = [
  "Bridgewatch",
  "Brecilien",
  "Caerleon",
  "Fort Sterling",
  "Lymhurst",
  "Martlock",
  "Thetford",
];

const QUALITY_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "Normal" },
  { value: 2, label: "Bom" },
  { value: 3, label: "Notável" },
  { value: 4, label: "Excelente" },
  { value: 5, label: "Obra-prima" },
];

/* ── Weights type ── */

interface Weights {
  profit_weight: number;
  focus_weight: number;
  volume_weight: number;
  freshness_weight: number;
}

/* ── Filter values read from URL ── */

export interface FilterValues {
  market: MarketMode;
  category: string;
  tier: string;
  enchantment: string;
  city: string;
  quality: string;
  minProfit: string;
  w_profit: string;
  w_focus: string;
  w_volume: string;
  w_freshness: string;
  excludeCaerleon: string;
  useFocus: string;
  nameSearch: string;
}

/* ── Active Chip ── */

interface ActiveChip {
  key: string;
  label: string;
  value: string;
}

export function ActiveFilterChips({
  filters,
  onRemove,
}: {
  filters: FilterValues;
  onRemove: (key: string) => void;
}) {
  const chips: ActiveChip[] = [];

  if (filters.market !== "marketplace") {
    chips.push({
      key: "market",
      label: "Mercado",
      value: "Mercado Negro",
    });
  }
  if (filters.category) chips.push({ key: "category", label: "Categoria", value: CATEGORY_LABELS[filters.category] ?? filters.category });
  if (filters.tier) chips.push({ key: "tier", label: "Tier", value: `T${filters.tier}` });
  if (filters.enchantment) {
    const encLevel = parseInt(filters.enchantment);
    const stars = "★".repeat(encLevel) + "☆".repeat(Math.max(0, 4 - encLevel));
    chips.push({ key: "enchantment", label: "Enc", value: stars });
  }
  if (filters.city) chips.push({ key: "city", label: "Cidade", value: filters.city });
  if (filters.quality) {
    const q = QUALITY_OPTIONS.find((o) => String(o.value) === filters.quality);
    chips.push({ key: "quality", label: "Qualidade", value: q?.label ?? filters.quality });
  }
  if (filters.minProfit) chips.push({ key: "min_profit", label: "Lucro Mín.", value: `${filters.minProfit}s` });
  if (filters.excludeCaerleon !== "true") chips.push({ key: "exclude_caerleon", label: "Caerleon", value: "Incluído" });
  if (filters.useFocus === "true") chips.push({ key: "use_focus", label: "Foco", value: "Ativado" });
  if (filters.nameSearch) chips.push({ key: "q", label: "Busca", value: filters.nameSearch });

  if (chips.length === 0) return null;

  return (
    <div className="mb-4 flex flex-wrap gap-2" role="list" aria-label="Filtros ativos">
      {chips.map((chip) => (
        <span
          key={chip.key}
          role="listitem"
          className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs"
          style={{
            background: "var(--color-bg-overlay)",
            borderColor: "var(--color-border-default)",
            color: "var(--color-text-secondary)",
          }}
        >
          <span style={{ color: "var(--color-text-muted)" }}>{chip.label}:</span>
          <span style={{ color: "var(--color-text-primary)" }}>{chip.value}</span>
          <button
            onClick={() => onRemove(chip.key)}
            aria-label={`Remover filtro ${chip.label}`}
            className="ml-0.5 rounded-full p-0.5 transition-colors"
            style={{ color: "var(--color-text-muted)" }}
          >
            ✕
          </button>
        </span>
      ))}
    </div>
  );
}

/* ── Select wrapper ── */

function FilterSelect({
  id,
  label,
  value,
  onChange,
  options,
  placeholder,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder: string;
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1 block text-xs font-medium"
        style={{ color: "var(--color-text-secondary)" }}
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border px-3 py-2 text-sm"
        style={{
          background: "var(--color-bg-canvas)",
          borderColor: "var(--color-border-default)",
          color: "var(--color-text-primary)",
        }}
      >
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

/* ── Segmented buttons for Tier / Enchantment ── */

function SegmentedFilter({
  label,
  value,
  options,
  onChange,
  ariaLabel,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  ariaLabel: string;
}) {
  return (
    <div>
      <span
        className="mb-1 block text-xs font-medium"
        style={{ color: "var(--color-text-secondary)" }}
      >
        {label}
      </span>
      <div
        className="flex rounded-md border"
        role="group"
        aria-label={ariaLabel}
        style={{
          background: "var(--color-bg-canvas)",
          borderColor: "var(--color-border-default)",
        }}
      >
        {options.map((opt, i) => {
          const isSelected = opt.value === value;
          return (
            <button
              key={opt.value}
              onClick={() => onChange(isSelected ? "" : opt.value)}
              className="min-h-[44px] min-w-[44px] flex-1 px-2 py-2 text-xs font-medium transition-colors"
              style={{
                background: isSelected ? "var(--color-bg-overlay)" : "transparent",
                color: isSelected
                  ? "var(--color-accent-gold)"
                  : "var(--color-text-muted)",
                borderRight:
                  i < options.length - 1
                    ? "1px solid var(--color-border-default)"
                    : undefined,
              }}
              aria-pressed={isSelected}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ── Main FilterSidebar ── */

interface FilterSidebarProps {
  filters: FilterValues;
  onFilterChange: (key: string, value: string) => void;
  onReset: () => void;
  activeFilterCount: number;
}

export default function FilterSidebar({
  filters,
  onFilterChange,
  onReset,
  activeFilterCount,
}: FilterSidebarProps) {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  /* Weight state */
  const [weights, setWeights] = useState<Weights>({
    profit_weight: filters.w_profit ? parseFloat(filters.w_profit) : 0.25,
    focus_weight: filters.w_focus ? parseFloat(filters.w_focus) : 0.1,
    volume_weight: filters.w_volume ? parseFloat(filters.w_volume) : 0.55,
    freshness_weight: filters.w_freshness ? parseFloat(filters.w_freshness) : 0.1,
  });
  const [defaultWeights, setDefaultWeights] = useState<Weights | null>(null);

  useEffect(() => {
    fetchConfig()
      .then((cfg: ConfigResponse) => {
        const dw: Weights = {
          profit_weight: cfg.profit_weight,
          focus_weight: cfg.focus_weight,
          volume_weight: cfg.volume_weight,
          freshness_weight: cfg.freshness_weight,
        };
        setDefaultWeights(dw);
        // Only set weights from defaults if not overridden via URL
        if (!filters.w_profit && !filters.w_focus && !filters.w_volume && !filters.w_freshness) {
          setWeights(dw);
        }
      })
      .catch(() => {
        /* config fetch fail is non-fatal — keep local defaults */
      });
    // Only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* Focus trap for drawer */
  useEffect(() => {
    if (!isDrawerOpen) return;

    const drawer = drawerRef.current;
    if (!drawer) return;

    const focusable = drawer.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    first?.focus();

    function trapFocus(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsDrawerOpen(false);
        triggerRef.current?.focus();
        return;
      }
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }

    document.addEventListener("keydown", trapFocus);
    return () => document.removeEventListener("keydown", trapFocus);
  }, [isDrawerOpen]);

  /* Lock body scroll when drawer open */
  useEffect(() => {
    if (isDrawerOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isDrawerOpen]);

  const handleWeightChange = useCallback(
    (newWeights: Weights) => {
      setWeights(newWeights);
      onFilterChange("w_profit", newWeights.profit_weight.toFixed(2));
      onFilterChange("w_focus", newWeights.focus_weight.toFixed(2));
      onFilterChange("w_volume", newWeights.volume_weight.toFixed(2));
      onFilterChange("w_freshness", newWeights.freshness_weight.toFixed(2));
    },
    [onFilterChange],
  );

  const handleWeightReset = useCallback(() => {
    if (!defaultWeights) return;
    setWeights(defaultWeights);
    onFilterChange("w_profit", "");
    onFilterChange("w_focus", "");
    onFilterChange("w_volume", "");
    onFilterChange("w_freshness", "");
  }, [defaultWeights, onFilterChange]);

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleNameSearch = useCallback(
    (value: string) => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
      searchTimerRef.current = setTimeout(() => {
        onFilterChange("q", value);
      }, 300);
    },
    [onFilterChange],
  );

  const filterControls = (
    <div className="space-y-5">
      {/* Exclude Caerleon toggle */}
      <label
        className="flex cursor-pointer items-center gap-3"
        htmlFor="toggle-exclude-caerleon"
      >
        <div className="relative">
          <input
            id="toggle-exclude-caerleon"
            type="checkbox"
            checked={filters.excludeCaerleon === "true"}
            onChange={(e) =>
              onFilterChange("exclude_caerleon", e.target.checked ? "true" : "false")
            }
            className="peer sr-only"
          />
          <div
            className="h-6 w-11 rounded-full transition-colors peer-checked:bg-[var(--color-accent-gold)] peer-focus-visible:ring-2"
            style={{
              background: filters.excludeCaerleon === "true" ? "var(--color-accent-gold)" : "var(--color-bg-overlay)",
              border: "1px solid var(--color-border-default)",
            }}
          />
          <div
            className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full transition-transform peer-checked:translate-x-5"
            style={{ background: "var(--color-bg-canvas)" }}
          />
        </div>
        <span
          className="text-xs font-medium"
          style={{ color: "var(--color-text-secondary)" }}
        >
          Excluir Caerleon
        </span>
      </label>

      {/* Use Focus toggle */}
      <label
        className="flex cursor-pointer items-center gap-3"
        htmlFor="toggle-use-focus"
      >
        <div className="relative">
          <input
            id="toggle-use-focus"
            type="checkbox"
            checked={filters.useFocus === "true"}
            onChange={(e) =>
              onFilterChange("use_focus", e.target.checked ? "true" : "false")
            }
            className="peer sr-only"
          />
          <div
            className="h-6 w-11 rounded-full transition-colors peer-checked:bg-[var(--color-accent-gold)] peer-focus-visible:ring-2"
            style={{
              background: filters.useFocus === "true" ? "var(--color-accent-gold)" : "var(--color-bg-overlay)",
              border: "1px solid var(--color-border-default)",
            }}
          />
          <div
            className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full transition-transform peer-checked:translate-x-5"
            style={{ background: "var(--color-bg-canvas)" }}
          />
        </div>
        <span
          className="text-xs font-medium"
          style={{ color: "var(--color-text-secondary)" }}
        >
          Usar Foco
        </span>
      </label>

      {/* Name Search */}
      <div>
        <label
          htmlFor="filter-name-search"
          className="mb-1 block text-xs font-medium"
          style={{ color: "var(--color-text-secondary)" }}
        >
          Buscar item
        </label>
        <input
          id="filter-name-search"
          type="text"
          value={filters.nameSearch}
          onChange={(e) => handleNameSearch(e.target.value)}
          placeholder="Ex: Royal Armor"
          className="w-full rounded-md border px-3 py-2 text-sm"
          style={{
            background: "var(--color-bg-canvas)",
            borderColor: "var(--color-border-default)",
            color: "var(--color-text-primary)",
          }}
        />
      </div>

      {/* Market Mode */}
      <div>
        <span
          className="mb-2 block text-xs font-semibold uppercase tracking-wider"
          style={{
            fontFamily: "var(--font-cinzel), Cinzel, Georgia, serif",
            color: "var(--color-text-secondary)",
          }}
        >
          Modo de Mercado
        </span>
        <BlackMarketToggle
          value={filters.market}
          onChange={(mode) => onFilterChange("market", mode === "marketplace" ? "" : mode)}
        />
      </div>

      {/* Category */}
      <FilterSelect
        id="filter-category"
        label="Categoria"
        value={filters.category}
        onChange={(v) => onFilterChange("category", v)}
        options={CATEGORIES.map((c) => ({ value: c, label: CATEGORY_LABELS[c] ?? c }))}
        placeholder="Todas Categorias"
      />

      {/* Tier */}
      <SegmentedFilter
        label="Tier"
        value={filters.tier}
        options={TIERS.map((t) => ({ value: String(t), label: `T${t}` }))}
        onChange={(v) => onFilterChange("tier", v)}
        ariaLabel="Filtro de tier"
      />

      {/* Enchantment */}
      <SegmentedFilter
        label="Encantamento"
        value={filters.enchantment}
        options={ENCHANTMENTS.map((e) => ({ value: String(e), label: String(e) }))}
        onChange={(v) => onFilterChange("enchantment", v)}
        ariaLabel="Filtro de encantamento"
      />

      {/* City */}
      <FilterSelect
        id="filter-city"
        label="Cidade"
        value={filters.city}
        onChange={(v) => onFilterChange("city", v)}
        options={CITIES.map((c) => ({ value: c, label: c }))}
        placeholder="Melhor cidade"
      />

      {/* Quality */}
      <FilterSelect
        id="filter-quality"
        label="Qualidade"
        value={filters.quality}
        onChange={(v) => onFilterChange("quality", v)}
        options={QUALITY_OPTIONS.map((q) => ({ value: String(q.value), label: q.label }))}
        placeholder="Todas Qualidades"
      />

      {/* Min Profit */}
      <div>
        <label
          htmlFor="filter-min-profit"
          className="mb-1 block text-xs font-medium"
          style={{ color: "var(--color-text-secondary)" }}
        >
          Lucro Mínimo (silver)
        </label>
        <input
          id="filter-min-profit"
          type="number"
          min={0}
          step={100}
          value={filters.minProfit}
          onChange={(e) => onFilterChange("min_profit", e.target.value)}
          placeholder="0"
          className="w-full rounded-md border px-3 py-2 text-sm tabular-nums"
          style={{
            background: "var(--color-bg-canvas)",
            borderColor: "var(--color-border-default)",
            color: "var(--color-text-primary)",
            fontFamily: "var(--font-plex-mono), IBM Plex Mono, monospace",
          }}
        />
      </div>

      {/* Weights — behind <details> on mobile */}
      <details className="lg:open" open={undefined}>
        <summary
          className="cursor-pointer text-xs font-semibold uppercase tracking-wider lg:hidden"
          style={{
            fontFamily: "var(--font-cinzel), Cinzel, Georgia, serif",
            color: "var(--color-text-secondary)",
          }}
        >
          Pesos do Score
        </summary>
        <div className="mt-3 lg:mt-0">
          <WeightConfig
            weights={weights}
            onChange={handleWeightChange}
            defaults={defaultWeights}
            onReset={handleWeightReset}
          />
        </div>
      </details>

      {/* Reset */}
      <button
        onClick={onReset}
        className="w-full rounded-md border px-4 py-2 text-sm font-medium transition-colors"
        style={{
          background: "var(--color-bg-overlay)",
          borderColor: "var(--color-border-default)",
          color: "var(--color-text-primary)",
        }}
      >
        Limpar todos os filtros
      </button>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar — persistent */}
      <aside
        className="hidden w-80 shrink-0 lg:block"
        aria-label="Filtros"
      >
        <div
          className="sticky top-[65px] overflow-y-auto rounded-lg border p-4"
          style={{
            background: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-default)",
            maxHeight: "calc(100vh - 90px)",
          }}
        >
          <h2
            className="mb-4 text-sm font-bold uppercase tracking-wider"
            style={{
              fontFamily: "var(--font-cinzel), Cinzel, Georgia, serif",
              color: "var(--color-accent-gold)",
            }}
          >
            Filtros
          </h2>
          {filterControls}
        </div>
      </aside>

      {/* Mobile filter trigger */}
      <button
        ref={triggerRef}
        onClick={() => setIsDrawerOpen(true)}
        className="inline-flex min-h-[44px] items-center gap-2 rounded-md border px-3 py-2 text-xs font-medium lg:hidden"
        style={{
          background: "var(--color-bg-overlay)",
          borderColor: "var(--color-border-default)",
          color: "var(--color-text-primary)",
        }}
        aria-label="Abrir filtros"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M1 3h14M3 8h10M5 13h6"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        Filtros
        {activeFilterCount > 0 && (
          <span
            className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold"
            style={{
              background: "var(--color-accent-gold)",
              color: "var(--color-bg-canvas)",
            }}
          >
            {activeFilterCount}
          </span>
        )}
      </button>

      {/* Mobile drawer overlay + panel */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 motion-safe:transition-opacity"
            style={{ background: "rgba(0, 0, 0, 0.6)" }}
            onClick={() => setIsDrawerOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer panel */}
          <div
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Painel de filtros"
            className="absolute inset-y-0 left-0 w-72 overflow-y-auto border-r p-4 motion-safe:transition-transform"
            style={{
              background: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-default)",
            }}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2
                className="text-sm font-bold uppercase tracking-wider"
                style={{
                  fontFamily: "var(--font-cinzel), Cinzel, Georgia, serif",
                  color: "var(--color-accent-gold)",
                }}
              >
                Filtros
              </h2>
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="min-h-[44px] min-w-[44px] rounded p-2 text-sm"
                style={{ color: "var(--color-text-muted)" }}
                aria-label="Fechar filtros"
              >
                ✕
              </button>
            </div>
            {filterControls}
          </div>
        </div>
      )}
    </>
  );
}
