from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Material:
    item_id: str
    quantity: int
    is_artifact_component: bool = False


@dataclass(slots=True)
class Recipe:
    product_id: str
    category: str
    tier: int
    enchantment: int
    materials: list[Material]
    focus_cost: int
    amount_crafted: int = 1
    silver_cost: int = 0


@dataclass(frozen=True, slots=True)
class CityBonus:
    city: str
    category: str
    bonus_rate: float


@dataclass
class ScoringConfig:
    """Configuracao para o motor de ranqueamento v2.

    Pesos devem somar 1.0; validado em __post_init__.
    """

    quality: int = 1
    setup_fee_rate: float = 0.025
    premium_tax_rate: float = 0.04
    normal_tax_rate: float = 0.08
    is_premium: bool = True
    profit_weight: float = 0.25
    focus_weight: float = 0.1
    volume_weight: float = 0.55
    freshness_weight: float = 0.1
    min_profit: float = 0.0

    def __post_init__(self) -> None:
        total = (
            self.profit_weight
            + self.focus_weight
            + self.volume_weight
            + self.freshness_weight
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Pesos de pontuacao devem somar 1.0; atual: {total:.6f}"
            )

    @property
    def sales_tax_rate(self) -> float:
        """Taxa de venda efetiva com base no status premium."""
        return self.premium_tax_rate if self.is_premium else self.normal_tax_rate


@dataclass
class ScoredItem:
    """Resultado de pontuacao para um item craftavel (Scoring Engine v2).

    Campo primario: ``return_rate_pct`` — taxa de retorno percentual
    calculada como ``(profit_absolute / total_cost) * 100``.

    Campos de impostos *separados* (nao opaco):
      - ``setup_fee``  = 2.5 % do effective_craft_cost (taxa da estacao de craft)
      - ``sales_tax``  = 4 % (premium) ou 8 % (normal) sobre sell_price total

    Contrato para task_006 / task_007: itens com precos de materiais ou
    produto ausentes NAO aparecem aqui. O chamador pode detectar exclusoes
    comparando ``len(recipes)`` com ``len(ranked)``.
    Campos bm_* sao None a menos que ``sell_mode == "comparison"``.
    """

    product_id: str
    craft_city: str
    sell_mode: str  # "marketplace" | "black_market" | "comparison"
    material_cost: float
    effective_craft_cost: float
    setup_fee: float
    sales_tax: float
    sell_price: float
    net_revenue: float
    profit_absolute: float
    return_rate_pct: float  # PRIMARY METRIC
    focus_cost: int
    profit_per_focus: float
    freshness_score: float
    volume_score: float
    volume_norm: float
    best_city: str
    final_score: float
    # Comparison mode extras (None in other modes)
    bm_sell_price: float | None = None
    bm_net_revenue: float | None = None
    bm_profit: float | None = None
    bm_return_rate_pct: float | None = None
    display_name: str = ""
    silver_cost: int = 0