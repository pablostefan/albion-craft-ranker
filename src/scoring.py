from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .albion_client import AlbionAPIClient, MarketPrice
from .models import Material, Recipe, ScoredItem, ScoringConfig
from .rrr_engine import SUPPORTED_CITIES, get_effective_material_cost


@dataclass
class RecipeLine:
    product_id: str
    material_id: str
    material_qty: float
    focus_cost: float


@dataclass
class RankedItem:
    product_id: str
    material_cost: float
    effective_craft_cost: float
    sell_price_min: float
    net_revenue: float
    profit: float
    margin_pct: float
    focus_cost: float
    profit_per_focus: float
    volume_score: float
    final_score: float


def load_recipes(csv_path: Path) -> List[RecipeLine]:
    rows: List[RecipeLine] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"product_id", "material_id", "material_qty"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV sem colunas obrigatorias: {sorted(missing)}")

        for raw in reader:
            rows.append(
                RecipeLine(
                    product_id=str(raw["product_id"]).strip(),
                    material_id=str(raw["material_id"]).strip(),
                    material_qty=float(raw["material_qty"] or 0),
                    focus_cost=float(raw.get("focus_cost") or 0),
                )
            )
    return rows


def _chunk(items: Iterable[str], size: int) -> List[List[str]]:
    lst = list(dict.fromkeys(items))
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def _index_prices(prices: Iterable[MarketPrice]) -> Dict[Tuple[str, str], MarketPrice]:
    out: Dict[Tuple[str, str], MarketPrice] = {}
    for p in prices:
        out[(p.item_id, p.city)] = p
    return out


def _extract_daily_volume(history_rows: List[dict]) -> float:
    points: List[float] = []
    for row in history_rows:
        # O endpoint pode retornar formatos diferentes; tentamos os campos mais comuns.
        candidates = [
            row.get("item_count"),
            row.get("count"),
            row.get("amount"),
            row.get("volume"),
        ]
        value = None
        for c in candidates:
            if c is not None:
                try:
                    value = float(c)
                    break
                except (TypeError, ValueError):
                    pass
        if value is not None and value > 0:
            points.append(value)

    if not points:
        return 0.0
    return statistics.median(points)


def _normalize(values: List[float]) -> List[float]:
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if math.isclose(vmin, vmax):
        return [1.0 for _ in values]
    return [(v - vmin) / (vmax - vmin) for v in values]


def rank_items(
    client: AlbionAPIClient,
    recipe_lines: List[RecipeLine],
    craft_city: str,
    sell_city: str,
    quality: int,
    return_rate: float,
    tax_rate: float,
    volume_days: int,
    profit_weight: float,
    volume_weight: float,
    min_profit: float,
    use_history: bool = False,
) -> List[RankedItem]:
    products = sorted({r.product_id for r in recipe_lines})
    materials = sorted({r.material_id for r in recipe_lines})
    all_ids = sorted(set(products + materials))

    prices_all: List[MarketPrice] = []
    for batch in _chunk(all_ids, 120):
        prices_all.extend(client.get_prices(batch, [craft_city, sell_city], quality))

    price_idx = _index_prices(prices_all)

    volume_by_product: Dict[str, float] = {}
    if use_history:
        for batch in _chunk(products, 40):
            history_by_item = client.get_history_bulk(batch, sell_city, quality, days=volume_days)
            for product in batch:
                volume_by_product[product] = _extract_daily_volume(history_by_item.get(product, []))

    grouped: Dict[str, List[RecipeLine]] = {}
    for line in recipe_lines:
        grouped.setdefault(line.product_id, []).append(line)

    ranked: List[RankedItem] = []
    for product_id, lines in grouped.items():
        material_cost = 0.0
        missing_material_price = False
        for line in lines:
            mp = price_idx.get((line.material_id, craft_city))
            if not mp:
                missing_material_price = True
                break

            # Para custo de compra de material, usar preco de venda do mercado local.
            unit_material_price = mp.sell_price_min if mp.sell_price_min > 0 else mp.buy_price_max
            if unit_material_price <= 0:
                missing_material_price = True
                break

            material_cost += line.material_qty * unit_material_price

        product_price = price_idx.get((product_id, sell_city))
        if (
            missing_material_price
            or material_cost <= 0
            or not product_price
            or product_price.sell_price_min <= 0
        ):
            continue

        effective_craft_cost = material_cost * (1.0 - return_rate)
        net_revenue = product_price.sell_price_min * (1.0 - tax_rate)
        profit = net_revenue - effective_craft_cost
        if profit < min_profit:
            continue

        margin_pct = (profit / effective_craft_cost * 100.0) if effective_craft_cost > 0 else 0.0
        focus_cost = max(line.focus_cost for line in lines)
        profit_per_focus = (profit / focus_cost) if focus_cost > 0 else 0.0

        volume_value = volume_by_product.get(product_id, 0.0)
        if not use_history:
            volume_value = max(product_price.buy_price_max, 0.0)

        ranked.append(
            RankedItem(
                product_id=product_id,
                material_cost=material_cost,
                effective_craft_cost=effective_craft_cost,
                sell_price_min=product_price.sell_price_min,
                net_revenue=net_revenue,
                profit=profit,
                margin_pct=margin_pct,
                focus_cost=focus_cost,
                profit_per_focus=profit_per_focus,
                volume_score=volume_value,
                final_score=0.0,
            )
        )

    profit_norm = _normalize([r.profit for r in ranked])
    vol_norm = _normalize([r.volume_score for r in ranked])

    for i, item in enumerate(ranked):
        item.final_score = profit_weight * profit_norm[i] + volume_weight * vol_norm[i]

    ranked.sort(key=lambda x: (x.final_score, x.profit, x.volume_score), reverse=True)
    return ranked


def save_ranking_csv(items: List[RankedItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "product_id",
                "material_cost",
                "effective_craft_cost",
                "sell_price_min",
                "net_revenue",
                "profit",
                "margin_pct",
                "focus_cost",
                "profit_per_focus",
                "volume_score",
                "final_score",
            ]
        )
        for i in items:
            w.writerow(
                [
                    i.product_id,
                    round(i.material_cost, 2),
                    round(i.effective_craft_cost, 2),
                    round(i.sell_price_min, 2),
                    round(i.net_revenue, 2),
                    round(i.profit, 2),
                    round(i.margin_pct, 2),
                    round(i.focus_cost, 2),
                    round(i.profit_per_focus, 4),
                    round(i.volume_score, 2),
                    round(i.final_score, 4),
                ]
            )


# =============================================================================
# Scoring Engine v2
# =============================================================================

_SELL_MODES: frozenset[str] = frozenset({"marketplace", "black_market", "comparison"})
_BM_LOCATION = "Black Market"


def _freshness(staleness_hours: float, cap_hours: float) -> float:
    """freshness_score em [0.0, 1.0]: 1.0 para preco recente, 0.0 para obsoleto."""
    return max(0.0, 1.0 - staleness_hours / cap_hours)


def _get_unit_prices(
    materials: List[Material],
    price_idx: Dict[Tuple[str, str], MarketPrice],
    city: str,
) -> Dict[str, float] | None:
    """Retorna {material_id: unit_price} para a cidade.

    Contrato para task_006 / task_007: retorna None quando qualquer material
    estiver sem preco valido; o chamador registra o item como
    ``item_skipped=missing_material_price`` nos metadados da resposta.
    """
    unit_prices: Dict[str, float] = {}
    for m in materials:
        mp = price_idx.get((m.item_id, city))
        if mp is None:
            return None
        price = mp.sell_price_min if mp.sell_price_min > 0 else mp.buy_price_max
        if price <= 0:
            return None
        unit_prices[m.item_id] = price
    return unit_prices


def _raw_material_cost(
    materials: List[Material], unit_prices: Dict[str, float]
) -> float:
    """Custo bruto total dos materiais (sem aplicar RRR)."""
    return sum(m.quantity * unit_prices[m.item_id] for m in materials)


def find_cheapest_city_per_material(
    materials: List[Material],
    price_idx: Dict[Tuple[str, str], MarketPrice],
    cities: tuple[str, ...] = SUPPORTED_CITIES,
) -> Dict[str, Tuple[str, float]]:
    """For each material, find the city with the lowest price.

    Uses same price logic as _get_unit_prices: sell_price_min, fallback buy_price_max.
    Returns {material_item_id: (cheapest_city, cheapest_price)}.
    """
    result: Dict[str, Tuple[str, float]] = {}
    for m in materials:
        best_city: str | None = None
        best_price = float("inf")
        for city in cities:
            mp = price_idx.get((m.item_id, city))
            if mp is None:
                continue
            price = mp.sell_price_min if mp.sell_price_min > 0 else mp.buy_price_max
            if 0 < price < best_price:
                best_price = price
                best_city = city
        if best_city is not None:
            result[m.item_id] = (best_city, best_price)
    return result


def _find_best_city(
    recipe: Recipe,
    sell_mode: str,
    use_focus: bool,
    spec_bonus: float,
    config: ScoringConfig,
    price_idx: Dict[Tuple[str, str], MarketPrice],
    city_bonuses: Dict[str, Dict[str, float]] | None,
    staleness_cap_hours: float,
    exclude_cities: frozenset[str] = frozenset(),
) -> str:
    """Retorna a cidade onde return_rate_pct e maximo para a receita.

    Itera SUPPORTED_CITIES e pula cidades sem precos disponiveis.
    Para sell_mode='comparison', usa marketplace como base de comparacao.
    """
    effective_sell_mode = "marketplace" if sell_mode == "comparison" else sell_mode
    available = [c for c in SUPPORTED_CITIES if c not in exclude_cities]
    best_city = available[0] if available else SUPPORTED_CITIES[0]
    best_rr = -math.inf

    for city in SUPPORTED_CITIES:
        if city in exclude_cities:
            continue
        unit_prices = _get_unit_prices(recipe.materials, price_idx, city)
        if unit_prices is None:
            continue
        try:
            eff_cost = get_effective_material_cost(
                recipe.materials,
                unit_prices,
                category=recipe.category,
                city=city,
                use_focus=use_focus,
                spec_bonus=spec_bonus,
                city_bonuses=city_bonuses,
            )
        except (KeyError, ValueError):
            continue

        setup = eff_cost * config.setup_fee_rate
        total_cost = eff_cost + setup
        if total_cost <= 0:
            continue

        if effective_sell_mode == "black_market":
            mp = price_idx.get((recipe.product_id, _BM_LOCATION))
            sell_price = mp.buy_price_max if mp is not None else 0.0
        else:
            mp = price_idx.get((recipe.product_id, city))
            sell_price = mp.sell_price_min if mp is not None else 0.0

        if sell_price <= 0:
            continue

        total_sell = sell_price * recipe.amount_crafted
        sales_tax = total_sell * config.sales_tax_rate
        net_revenue = total_sell - sales_tax
        profit = net_revenue - total_cost
        rr = profit / total_cost * 100.0
        if rr > best_rr:
            best_rr = rr
            best_city = city

    return best_city


def rank_items_v2(
    recipes: List[Recipe],
    prices: Iterable[MarketPrice],
    city_bonuses: Dict[str, Dict[str, float]] | None,
    config: ScoringConfig,
    *,
    craft_city: str = "Lymhurst",
    sell_city: str | None = None,
    sell_mode: str = "marketplace",
    use_focus: bool = False,
    spec_bonus: float = 0.0,
    quality: int = 1,
    staleness_cap_hours: float = 48.0,
    exclude_cities: frozenset[str] = frozenset(),
) -> List[ScoredItem]:
    """Motor de ranqueamento v2.

    Integra list[Recipe] do parser, precos multi-cidade do AlbionAPIClient e
    calculos dinamicos de RRR do rrr_engine.

    Parametros
    ----------
    recipes:
        Receitas obtidas de ``parse_items_json()``.
    prices:
        Precos de mercado (todos itens + todas as cidades necessarias).
    city_bonuses:
        Mapa city->category->bonus ou None (usa defaults do rrr_engine).
    config:
        Configuracao de pesos, taxas e filtros.
    craft_city:
        Cidade de criacao (determina RRR e custo de materiais).
    sell_city:
        Cidade de venda; padrao = craft_city.
    sell_mode:
        ``"marketplace"`` | ``"black_market"`` | ``"comparison"``.
    use_focus:
        Se True, aplica bonus de foco no calculo de RRR.
    spec_bonus:
        Bonus de especializacao (0-1 ou 0-100, normalizado internamente).
    quality:
        Qualidade do item para lookup de preco (1 = Normal).
    staleness_cap_hours:
        Horas apos as quais freshness_score cai para 0.0 (padrao 48h).

    Notas de contrato para task_006 / task_007
    ------------------------------------------
    * Itens com preco de material ou produto ausente sao silenciosamente
      omitidos. O chamador detecta exclusoes por ``len(recipes) - len(result)``.
    * ``sell_price`` em ScoredItem armazena o preco unitario de mercado;
      ``net_revenue`` ja reflete ``amount_crafted`` (revenue total por craft).
    * Campos ``bm_*`` sao ``None`` exceto quando ``sell_mode='comparison'``.
    """
    if sell_mode not in _SELL_MODES:
        raise ValueError(
            f"sell_mode invalido: {sell_mode!r}. Valores validos: {sorted(_SELL_MODES)}"
        )

    _sell_city = sell_city or craft_city
    price_idx = _index_prices(prices)
    scored: List[ScoredItem] = []

    for recipe in recipes:
        # ── 1. Material prices ────────────────────────────────────────────
        unit_prices = _get_unit_prices(recipe.materials, price_idx, craft_city)
        if unit_prices is None:
            continue  # missing material price → skip silently

        material_cost = _raw_material_cost(recipe.materials, unit_prices)
        try:
            effective_craft_cost = get_effective_material_cost(
                recipe.materials,
                unit_prices,
                category=recipe.category,
                city=craft_city,
                use_focus=use_focus,
                spec_bonus=spec_bonus,
                city_bonuses=city_bonuses,
            )
        except (KeyError, ValueError):
            continue

        # ── 2. Setup fee (2.5% of craft cost) ────────────────────────────
        setup_fee = effective_craft_cost * config.setup_fee_rate
        total_cost = effective_craft_cost + setup_fee

        # ── 3. Sell-side revenue ──────────────────────────────────────────
        sell_price: float = 0.0
        sales_tax: float = 0.0
        net_revenue: float = 0.0
        freshness_hours: float = 0.0
        volume: float = 0.0

        mp_sell = price_idx.get((recipe.product_id, _sell_city))
        mp_bm = price_idx.get((recipe.product_id, _BM_LOCATION))

        if sell_mode in ("marketplace", "comparison"):
            if mp_sell is None or mp_sell.sell_price_min <= 0:
                if sell_mode == "marketplace":
                    continue  # no sell price → skip
                # comparison: marketplace part absent, BM below may still fire
            else:
                sell_price = mp_sell.sell_price_min
                total_sell = sell_price * recipe.amount_crafted
                sales_tax = total_sell * config.sales_tax_rate
                net_revenue = total_sell - sales_tax
                freshness_hours = mp_sell.staleness_hours
                volume = max(mp_sell.buy_price_max, 0.0)

        if sell_mode == "black_market":
            if mp_bm is None or mp_bm.buy_price_max <= 0:
                continue  # no BM price → skip
            sell_price = mp_bm.buy_price_max
            total_sell = sell_price * recipe.amount_crafted
            sales_tax = total_sell * config.sales_tax_rate
            net_revenue = total_sell - sales_tax
            freshness_hours = mp_bm.staleness_hours
            volume = sell_price

        # For comparison mode, skip entirely if neither source has revenue
        if sell_mode == "comparison" and net_revenue <= 0:
            continue

        profit = net_revenue - total_cost
        if profit < config.min_profit:
            continue

        return_rate_pct = (profit / total_cost * 100.0) if total_cost > 0 else 0.0

        # ── 4. Focus profit ───────────────────────────────────────────────
        if recipe.focus_cost > 0:
            try:
                eff_no_focus = get_effective_material_cost(
                    recipe.materials, unit_prices,
                    category=recipe.category, city=craft_city,
                    use_focus=False, spec_bonus=spec_bonus,
                    city_bonuses=city_bonuses,
                )
                eff_with_focus = get_effective_material_cost(
                    recipe.materials, unit_prices,
                    category=recipe.category, city=craft_city,
                    use_focus=True, spec_bonus=spec_bonus,
                    city_bonuses=city_bonuses,
                )
            except (KeyError, ValueError):
                eff_no_focus = effective_craft_cost
                eff_with_focus = effective_craft_cost
            cost_saving = eff_no_focus - eff_with_focus
            profit_per_focus = (cost_saving * (1.0 + config.setup_fee_rate)) / recipe.focus_cost
        else:
            profit_per_focus = 0.0

        # ── 5. Freshness score ────────────────────────────────────────────
        freshness_score = _freshness(freshness_hours, staleness_cap_hours)

        # ── 6. Black Market comparison fields ─────────────────────────────
        bm_sell_price: float | None = None
        bm_net_revenue: float | None = None
        bm_profit: float | None = None
        bm_return_rate_pct: float | None = None

        if sell_mode == "comparison" and mp_bm is not None and mp_bm.buy_price_max > 0:
            bm_sell = mp_bm.buy_price_max
            bm_total_sell = bm_sell * recipe.amount_crafted
            bm_tax = bm_total_sell * config.sales_tax_rate
            bm_sell_price = bm_sell
            bm_net_revenue = bm_total_sell - bm_tax
            bm_profit = bm_net_revenue - total_cost
            bm_return_rate_pct = (
                bm_profit / total_cost * 100.0 if total_cost > 0 else 0.0
            )

        # ── 7. Best city (cross-city optimization) ────────────────────────
        best_city = _find_best_city(
            recipe,
            sell_mode=sell_mode,
            use_focus=use_focus,
            spec_bonus=spec_bonus,
            config=config,
            price_idx=price_idx,
            city_bonuses=city_bonuses,
            staleness_cap_hours=staleness_cap_hours,
            exclude_cities=exclude_cities,
        )

        scored.append(
            ScoredItem(
                product_id=recipe.product_id,
                craft_city=craft_city,
                sell_mode=sell_mode,
                material_cost=material_cost,
                effective_craft_cost=effective_craft_cost,
                setup_fee=setup_fee,
                sales_tax=sales_tax,
                sell_price=sell_price,
                net_revenue=net_revenue,
                profit_absolute=profit,
                return_rate_pct=return_rate_pct,
                focus_cost=recipe.focus_cost,
                profit_per_focus=profit_per_focus,
                freshness_score=freshness_score,
                volume_score=volume,
                volume_norm=0.0,  # filled after normalization
                best_city=best_city,
                final_score=0.0,  # filled after normalization
                bm_sell_price=bm_sell_price,
                bm_net_revenue=bm_net_revenue,
                bm_profit=bm_profit,
                bm_return_rate_pct=bm_return_rate_pct,
            )
        )

    if not scored:
        return []

    # ── 8. Normalize components and compute final_score ───────────────────
    rr_norm = _normalize([s.return_rate_pct for s in scored])
    pf_norm = _normalize([s.profit_per_focus for s in scored])
    vol_norm = _normalize([s.volume_score for s in scored])
    # freshness_score is already in [0, 1]; no normalization needed

    for i, item in enumerate(scored):
        item.volume_norm = vol_norm[i]
        additive_score = (
            config.profit_weight * rr_norm[i]
            + config.focus_weight * pf_norm[i]
            + config.volume_weight * vol_norm[i]
            + config.freshness_weight * item.freshness_score
        )
        # Multiplicative volume gate: low-volume items are severely
        # penalised regardless of profit. Floor of 0.10 avoids total zeroing.
        vol_gate = 0.10 + 0.90 * vol_norm[i]
        item.final_score = additive_score * vol_gate

    scored.sort(
        key=lambda x: (x.final_score, x.return_rate_pct, x.profit_absolute),
        reverse=True,
    )
    return scored
