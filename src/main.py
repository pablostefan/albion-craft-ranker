from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List

from .albion_client import AlbionAPIClient, PRD_CITY_LOCATIONS
from .models import ScoredItem, ScoringConfig
from .recipe_parser import parse_items_json
from .rrr_engine import load_city_bonuses
from .scoring import (
    RankedItem,
    load_recipes,
    rank_items,
    rank_items_v2,
    save_ranking_csv,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Rankeia melhores itens para craftar no Albion (lucro + volume)."
    )

    # ── Source selection ───────────────────────────────────────────────────
    p.add_argument(
        "--items-json",
        default=None,
        help="Caminho do items.json (ao-bin-dumps). Modo v2.",
    )
    p.add_argument(
        "--modifiers-json",
        default=None,
        help="Caminho do craftingmodifiers.json para bonus de cidade.",
    )
    p.add_argument(
        "--recipes",
        default=None,
        help="Caminho do CSV de receitas (modo legado).",
    )

    # ── Core parameters ───────────────────────────────────────────────────
    p.add_argument("--server", default="west", choices=["west", "east", "europe"])
    p.add_argument("--craft-city", required=True, help="Cidade onde compra materiais/crafta")
    p.add_argument("--sell-city", default=None, help="Cidade onde vende (padrao = craft-city)")
    p.add_argument("--quality", type=int, default=1)

    # ── V2 scoring flags ─────────────────────────────────────────────────
    p.add_argument(
        "--sell-mode",
        default="marketplace",
        choices=["marketplace", "black_market", "comparison"],
        help="Modo de venda: marketplace, black_market ou comparison.",
    )
    p.add_argument(
        "--premium",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Premium ativo (4%% tax). Use --no-premium para 8%%.",
    )
    p.add_argument(
        "--use-focus",
        action="store_true",
        default=False,
        help="Habilita calculo de profit_per_focus com bonus de foco.",
    )
    p.add_argument("--focus-weight", type=float, default=0.2, help="Peso do profit_per_focus no score final.")
    p.add_argument("--freshness-weight", type=float, default=0.1, help="Peso do freshness no score final.")
    p.add_argument("--best-city", action="store_true", default=False, help="Habilita otimizacao cross-city.")

    # ── Legacy parameters (backward compat) ───────────────────────────────
    p.add_argument("--return-rate", type=float, default=0.152)
    p.add_argument("--tax-rate", type=float, default=0.065)
    p.add_argument("--volume-days", type=int, default=7)
    p.add_argument("--use-history", action="store_true", help="Usa endpoint de historico para volume diario.")
    p.add_argument("--profit-weight", type=float, default=0.7)
    p.add_argument("--volume-weight", type=float, default=0.3)
    p.add_argument("--min-profit", type=float, default=0.0)

    # ── Output ────────────────────────────────────────────────────────────
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--out", default="output/ranking.csv")

    return p


# ═══════════════════════════════════════════════════════════════════════════
# V2 output helpers
# ═══════════════════════════════════════════════════════════════════════════

_V2_CSV_COLUMNS = [
    "product_id",
    "craft_city",
    "sell_mode",
    "material_cost",
    "effective_craft_cost",
    "setup_fee",
    "sales_tax",
    "sell_price",
    "net_revenue",
    "profit_absolute",
    "return_rate_pct",
    "focus_cost",
    "profit_per_focus",
    "freshness_score",
    "volume_score",
    "best_city",
    "final_score",
]


def save_ranking_csv_v2(items: List[ScoredItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(_V2_CSV_COLUMNS)
        for item in items:
            w.writerow([
                item.product_id,
                item.craft_city,
                item.sell_mode,
                round(item.material_cost, 2),
                round(item.effective_craft_cost, 2),
                round(item.setup_fee, 2),
                round(item.sales_tax, 2),
                round(item.sell_price, 2),
                round(item.net_revenue, 2),
                round(item.profit_absolute, 2),
                round(item.return_rate_pct, 2),
                item.focus_cost,
                round(item.profit_per_focus, 4),
                round(item.freshness_score, 4),
                round(item.volume_score, 2),
                item.best_city,
                round(item.final_score, 4),
            ])


def print_table_v2(items: List[ScoredItem], top: int) -> None:
    print("\nTOP ITENS PARA CRAFT (Scoring Engine v2)")
    print(
        f"{'pos':<4} {'item':<30} {'return%':>8} {'profit':>10} "
        f"{'p/focus':>8} {'fresh':>6} {'best_city':<14} {'score':>7}"
    )
    print("-" * 92)
    for i, it in enumerate(items[:top], start=1):
        print(
            f"{i:<4} {it.product_id:<30} {it.return_rate_pct:>7.1f}% "
            f"{it.profit_absolute:>10.0f} {it.profit_per_focus:>8.2f} "
            f"{it.freshness_score:>5.2f} {it.best_city:<14} {it.final_score:>7.4f}"
        )


def print_table_legacy(items: List[RankedItem], top: int) -> None:
    print("\nTOP ITENS PARA CRAFT (lucro + saida)")
    print(
        "pos\titem\tfinal_score\tprofit\tmargin%\tvol\tprofit/focus"
    )
    for i, it in enumerate(items[:top], start=1):
        print(
            f"{i}\t{it.product_id}\t{it.final_score:.4f}\t{it.profit:.0f}\t"
            f"{it.margin_pct:.1f}%\t{it.volume_score:.1f}\t{it.profit_per_focus:.2f}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Entrypoints
# ═══════════════════════════════════════════════════════════════════════════

def _run_v2(args: argparse.Namespace) -> None:
    """items.json → recipes → prices → scoring → ranking CSV."""
    recipes = parse_items_json(args.items_json)
    if not recipes:
        print("Nenhuma receita encontrada no items.json.")
        return

    city_bonuses = None
    if args.modifiers_json:
        city_bonuses = load_city_bonuses(args.modifiers_json)

    config = ScoringConfig(
        is_premium=args.premium,
        focus_weight=args.focus_weight,
        freshness_weight=args.freshness_weight,
        min_profit=args.min_profit,
    )

    client = AlbionAPIClient(server=args.server)
    try:
        all_item_ids: set[str] = set()
        for r in recipes:
            all_item_ids.add(r.product_id)
            for m in r.materials:
                all_item_ids.add(m.item_id)

        prices = client.get_prices_all_cities(sorted(all_item_ids), args.quality)

        sell_city = args.sell_city or args.craft_city
        ranked = rank_items_v2(
            recipes,
            prices,
            city_bonuses,
            config,
            craft_city=args.craft_city,
            sell_city=sell_city,
            sell_mode=args.sell_mode,
            use_focus=args.use_focus,
        )
    finally:
        client.close()

    if not ranked:
        print("Nenhum item elegivel encontrado. Verifique items.json, precos e cidade.")
        return

    save_ranking_csv_v2(ranked, Path(args.out))
    print_table_v2(ranked, args.top)
    print(f"\nArquivo gerado: {args.out}")
    print(f"Total receitas: {len(recipes)} | Ranqueados: {len(ranked)}")


def _run_legacy(args: argparse.Namespace) -> None:
    """CSV mode — backward compatible with v1 CLI."""
    sell_city = args.sell_city
    if not sell_city:
        print("Erro: --sell-city e obrigatorio no modo legado (--recipes).", file=sys.stderr)
        sys.exit(1)

    if abs((args.profit_weight + args.volume_weight) - 1.0) > 1e-9:
        raise ValueError("profit_weight + volume_weight precisa ser 1.0")

    recipe_lines = load_recipes(Path(args.recipes))
    client = AlbionAPIClient(server=args.server)
    try:
        ranked = rank_items(
            client=client,
            recipe_lines=recipe_lines,
            craft_city=args.craft_city,
            sell_city=sell_city,
            quality=args.quality,
            return_rate=args.return_rate,
            tax_rate=args.tax_rate,
            volume_days=args.volume_days,
            profit_weight=args.profit_weight,
            volume_weight=args.volume_weight,
            min_profit=args.min_profit,
            use_history=args.use_history,
        )
    finally:
        client.close()

    if not ranked:
        print("Nenhum item elegivel encontrado. Verifique receitas, cidades e quality.")
        return

    save_ranking_csv(ranked, Path(args.out))
    print_table_legacy(ranked, args.top)
    print(f"\nArquivo gerado: {args.out}")


def main() -> None:
    args = build_parser().parse_args()

    if args.items_json:
        _run_v2(args)
    elif args.recipes:
        _run_legacy(args)
    else:
        print(
            "Erro: forneca --items-json (modo v2) ou --recipes (modo legado).",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
