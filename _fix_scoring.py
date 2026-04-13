"""Fix script: dedent v2 code in scoring.py to module level."""
with open("src/scoring.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Keep lines 0..242 (file lines 1..243 = save_ranking_csv excluding nested v2 code)
clean_prefix = "".join(lines[:243])

v2_code = r"""

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


def _find_best_city(
    recipe: Recipe,
    sell_mode: str,
    use_focus: bool,
    spec_bonus: float,
    config: ScoringConfig,
    price_idx: Dict[Tuple[str, str], MarketPrice],
    city_bonuses: Dict[str, Dict[str, float]] | None,
    staleness_cap_hours: float,
) -> str:
    """Retorna a cidade onde return_rate_pct e maximo para a receita.

    Itera SUPPORTED_CITIES e pula cidades sem precos disponiveis.
    Para sell_mode='comparison', usa marketplace como base de comparacao.
    """
    effective_sell_mode = "marketplace" if sell_mode == "comparison" else sell_mode
    best_city = SUPPORTED_CITIES[0]
    best_rr = -math.inf

    for city in SUPPORTED_CITIES:
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
    craft_city: str,
    sell_city: str | None = None,
    sell_mode: str = "marketplace",
    use_focus: bool = False,
    spec_bonus: float = 0.0,
    quality: int = 1,
    staleness_cap_hours: float = 48.0,
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
        # 1. Material prices
        unit_prices = _get_unit_prices(recipe.materials, price_idx, craft_city)
        if unit_prices is None:
            continue  # missing material price -> skip silently

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

        # 2. Setup fee (2.5% of craft cost)
        setup_fee = effective_craft_cost * config.setup_fee_rate
        total_cost = effective_craft_cost + setup_fee

        # 3. Sell-side revenue
        sell_price: float = 0.0
        sales_tax: float = 0.0
        net_revenue: float = 0.0
        freshness_hours: float = 0.0
        liquidity: float = 0.0

        mp_sell = price_idx.get((recipe.product_id, _sell_city))
        mp_bm = price_idx.get((recipe.product_id, _BM_LOCATION))

        if sell_mode in ("marketplace", "comparison"):
            if mp_sell is None or mp_sell.sell_price_min <= 0:
                if sell_mode == "marketplace":
                    continue  # no sell price -> skip
                # comparison: marketplace part absent, BM below may still fire
            else:
                sell_price = mp_sell.sell_price_min
                total_sell = sell_price * recipe.amount_crafted
                sales_tax = total_sell * config.sales_tax_rate
                net_revenue = total_sell - sales_tax
                freshness_hours = mp_sell.staleness_hours
                liquidity = max(mp_sell.buy_price_max, 0.0)

        if sell_mode == "black_market":
            if mp_bm is None or mp_bm.buy_price_max <= 0:
                continue  # no BM price -> skip
            sell_price = mp_bm.buy_price_max
            total_sell = sell_price * recipe.amount_crafted
            sales_tax = total_sell * config.sales_tax_rate
            net_revenue = total_sell - sales_tax
            freshness_hours = mp_bm.staleness_hours
            liquidity = sell_price

        # comparison mode: skip if no revenue from either source
        if sell_mode == "comparison" and net_revenue <= 0:
            continue

        profit = net_revenue - total_cost
        if profit < config.min_profit:
            continue

        return_rate_pct = (profit / total_cost * 100.0) if total_cost > 0 else 0.0

        # 4. Focus profit
        profit_per_focus = (profit / recipe.focus_cost) if recipe.focus_cost > 0 else 0.0

        # 5. Freshness score
        freshness_score = _freshness(freshness_hours, staleness_cap_hours)

        # 6. Black Market comparison fields
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

        # 7. Best city (cross-city optimization)
        best_city = _find_best_city(
            recipe,
            sell_mode=sell_mode,
            use_focus=use_focus,
            spec_bonus=spec_bonus,
            config=config,
            price_idx=price_idx,
            city_bonuses=city_bonuses,
            staleness_cap_hours=staleness_cap_hours,
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
                liquidity_score=liquidity,
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

    # 8. Normalize components and compute final_score
    rr_norm = _normalize([s.return_rate_pct for s in scored])
    pf_norm = _normalize([s.profit_per_focus for s in scored])
    liq_norm = _normalize([s.liquidity_score for s in scored])
    # freshness_score is already in [0, 1]; no normalization needed

    for i, item in enumerate(scored):
        item.final_score = (
            config.profit_weight * rr_norm[i]
            + config.focus_weight * pf_norm[i]
            + config.liquidity_weight * liq_norm[i]
            + config.freshness_weight * item.freshness_score
        )

    scored.sort(
        key=lambda x: (x.final_score, x.return_rate_pct, x.profit_absolute),
        reverse=True,
    )
    return scored
"""

new_content = clean_prefix + v2_code

with open("src/scoring.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("File written.")
with open("src/scoring.py", "r") as f:
    for i, line in enumerate(f, 1):
        if "def rank_items_v2" in line:
            print(f"  rank_items_v2 at line {i}: {repr(line)}")
        if "def _find_best_city" in line:
            print(f"  _find_best_city at line {i}: {repr(line)}")
