# API Reference

Base URL: `http://localhost:8000`

## GET /items

Retorna o ranking de itens craftáveis ordenados por score.

### Query Parameters

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `city` | string | `Lymhurst` | Cidade de craft |
| `category` | string | - | Filtro por categoria (ex: `warrior`, `hunter`, `mage`) |
| `tier` | int | - | Filtro por tier (2-8) |
| `enchantment` | int | - | Filtro por encantamento (0-4) |
| `quality` | int | - | Filtro por qualidade (1-5) |
| `market` | string | `marketplace` | `marketplace`, `black_market` ou `comparison` |
| `sell_city` | string | = city | Cidade de venda (para cross-city arbitrage) |
| `sort_by` | string | `return_rate_pct` | `return_rate_pct`, `profit`, `profit_per_focus`, `liquidity` |
| `order` | string | `desc` | `asc` ou `desc` |
| `limit` | int | `50` | Itens por página (1-500) |
| `offset` | int | `0` | Offset para paginação |
| `min_profit` | float | - | Lucro mínimo absoluto |
| `w_profit` | float | - | Peso profit (0-1), override temporário |
| `w_focus` | float | - | Peso focus (0-1), override temporário |
| `w_liquidity` | float | - | Peso liquidity (0-1), override temporário |
| `w_freshness` | float | - | Peso freshness (0-1), override temporário |

### Response

```json
{
  "items": [
    {
      "product_id": "T6_BAG",
      "craft_city": "Lymhurst",
      "sell_mode": "marketplace",
      "material_cost": 45000.0,
      "effective_craft_cost": 38250.0,
      "setup_fee": 956.25,
      "sales_tax": 2400.0,
      "sell_price": 60000.0,
      "net_revenue": 57600.0,
      "profit_absolute": 18393.75,
      "return_rate_pct": 46.9,
      "focus_cost": 120,
      "profit_per_focus": 35.5,
      "freshness_score": 0.85,
      "liquidity_score": 0.72,
      "best_city": "Lymhurst",
      "final_score": 0.89,
      "bm_sell_price": null,
      "bm_net_revenue": null,
      "bm_profit": null,
      "bm_return_rate_pct": null
    }
  ],
  "total": 3982,
  "filters_applied": {
    "city": "Lymhurst",
    "category": null,
    "tier": null,
    "enchantment": null,
    "market": "marketplace",
    "sell_city": null,
    "sort_by": "return_rate_pct"
  }
}
```

### Exemplo

```bash
curl "http://localhost:8000/items?city=Bridgewatch&tier=6&market=marketplace&sort_by=profit&limit=10"
```

---

## GET /items/{item_id}

Retorna detalhes de um item com breakdown de materiais e comparação entre cidades.

### Path Parameters

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `item_id` | string | ID do item (ex: `T6_BAG`) |

### Query Parameters

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `city` | string | `Lymhurst` | Cidade de craft |
| `market` | string | `marketplace` | `marketplace`, `black_market` ou `comparison` |
| `sell_city` | string | = city | Cidade de venda |

### Response

```json
{
  "item": { "...ScoredItemSchema..." },
  "cost_breakdown": [
    {
      "item_id": "T6_CLOTH",
      "quantity": 16,
      "unit_price": 2500.0,
      "total_price": 40000.0,
      "is_artifact_component": false
    }
  ],
  "city_comparison": [
    { "city": "Bridgewatch", "return_rate_pct": 42.1, "profit_absolute": 16500.0 },
    { "city": "Lymhurst", "return_rate_pct": 46.9, "profit_absolute": 18393.75 },
    { "city": "Fort Sterling", "return_rate_pct": 38.5, "profit_absolute": 14200.0 }
  ]
}
```

### Exemplo

```bash
curl "http://localhost:8000/items/T6_BAG?city=Lymhurst&market=marketplace"
```

---

## GET /cities

Retorna a lista de cidades com seus bônus de craft por categoria.

### Response

```json
{
  "cities": [
    {
      "name": "Bridgewatch",
      "bonuses": [
        { "category": "warrior", "bonus_pct": 15.0 },
        { "category": "crossbow", "bonus_pct": 15.0 }
      ]
    }
  ]
}
```

### Exemplo

```bash
curl "http://localhost:8000/cities"
```

---

## GET /config

Retorna a configuração atual do scoring engine.

### Response

```json
{
  "setup_fee_rate": 0.025,
  "premium_tax_rate": 0.04,
  "normal_tax_rate": 0.08,
  "is_premium": true,
  "profit_weight": 0.5,
  "focus_weight": 0.2,
  "liquidity_weight": 0.2,
  "freshness_weight": 0.1,
  "min_profit": 0.0,
  "sales_tax_rate": 0.04
}
```

### Exemplo

```bash
curl "http://localhost:8000/config"
```

---

## Schemas

### ScoredItemSchema

| Campo | Tipo | Descrição |
|---|---|---|
| `product_id` | string | ID do item |
| `craft_city` | string | Cidade de craft |
| `sell_mode` | string | marketplace / black_market / comparison |
| `material_cost` | float | Custo total dos materiais (sem RRR) |
| `effective_craft_cost` | float | Custo efetivo após RRR |
| `setup_fee` | float | Taxa de setup (2.5% do custo efetivo) |
| `sales_tax` | float | Taxa de venda (4% premium / 8% normal) |
| `sell_price` | float | Preço de venda (sell order min) |
| `net_revenue` | float | Receita líquida (preço - tax) |
| `profit_absolute` | float | Lucro absoluto em silver |
| `return_rate_pct` | float | Retorno percentual sobre custo |
| `focus_cost` | int | Custo de foco por craft |
| `profit_per_focus` | float | Silver por ponto de foco (delta) |
| `freshness_score` | float | Score de atualização dos preços (0-1) |
| `liquidity_score` | float | Score de liquidez do item (0-1) |
| `best_city` | string | Melhor cidade para craftar |
| `final_score` | float | Score final ponderado (0-1) |
| `bm_sell_price` | float? | Preço no Black Market (modo comparison) |
| `bm_net_revenue` | float? | Receita líquida BM |
| `bm_profit` | float? | Lucro BM |
| `bm_return_rate_pct` | float? | Retorno BM % |

### MaterialCost

| Campo | Tipo | Descrição |
|---|---|---|
| `item_id` | string | ID do material |
| `quantity` | int | Quantidade necessária |
| `unit_price` | float | Preço unitário |
| `total_price` | float | Preço total |
| `is_artifact_component` | bool | Se é componente de artefato |

### CityComparison

| Campo | Tipo | Descrição |
|---|---|---|
| `city` | string | Nome da cidade |
| `return_rate_pct` | float? | Retorno % |
| `profit_absolute` | float? | Lucro absoluto |
