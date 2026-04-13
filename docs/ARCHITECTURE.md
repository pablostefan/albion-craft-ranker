# Arquitetura

## Visão Geral

```
┌─────────────────┐      ┌────────────────────┐      ┌──────────────────┐
│   Next.js 15    │─────▶│   FastAPI Backend   │─────▶│   AODP API       │
│   (Frontend)    │◀─────│   (Python 3.12)     │◀─────│   (Preços)       │
└─────────────────┘      └────────────────────┘      └──────────────────┘
                                  │
                                  ▼
                         ┌────────────────────┐
                         │  ao-bin-dumps      │
                         │  items.json        │
                         │  (Receitas)        │
                         └────────────────────┘
```

## Fluxo de Dados

1. **Startup**: `items.json` é parseado em objetos `Recipe` (9.197 receitas)
2. **Background Refresh**: A cada 300s, preços são buscados na AODP API para todos os materiais e produtos
3. **Request**: Usuário faz query → cache hit ou scoring dinâmico → resposta JSON
4. **Frontend**: Next.js consome a API REST e renderiza tabelas, filtros e detalhes

## Componentes

### Backend (src/api/)

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| App Factory | `app.py` | `create_app()`, lifespan, CORS, background tasks |
| Routes | `routes/items.py` | GET /items, GET /items/{id} |
| Routes | `routes/cities.py` | GET /cities |
| Routes | `routes/config.py` | GET /config |
| Schemas | `schemas.py` | Modelos Pydantic para request/response |
| State | `dependencies.py` | `AppState` — receitas, preços, bônus, cache |
| Cache | `cache.py` | TTLCache com TTL de 300s |

### Scoring Engine (src/)

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| Scoring | `scoring.py` | `rank_items_v2()` — cálculo de métricas e score final |
| Config | `scoring.py` | `ScoringConfig` — taxas, pesos, flags |
| Recipe Parser | `recipe_parser.py` | Parse de items.json em objetos Recipe |

### Frontend (frontend/)

| Componente | Responsabilidade |
|---|---|
| `app/page.tsx` | Tabela principal de ranking |
| `app/items/[id]/page.tsx` | Detalhes do item com breakdown e comparação |
| `components/` | Filtros, seletores, tabelas reutilizáveis |
| `lib/api.ts` | Cliente HTTP para o backend |

## Decisões de Design

### RRR (Resource Return Rate) Dinâmico

O RRR varia por city + category. Cada cidade tem bônus de craft para categorias específicas:
- Sem bônus: 15.2% RRR
- Com bônus: 43.5% RRR (+36.7% do bônus de cidade)

O `effective_craft_cost` reflete o custo real após devolução de materiais.

### Profit per Focus (Delta)

```
profit_per_focus = (profit_com_foco - profit_sem_foco) / focus_cost
```

Mede o **valor marginal** do foco, não o lucro total dividido pelo foco. Isso evita inflar o score de itens que já são lucrativos sem foco.

### Separação de Taxas

- **Setup Fee**: 2.5% do custo efetivo (pago ao craftar)
- **Sales Tax**: 4% do preço de venda (premium) ou 8% (normal)
- Taxas são subtraídas separadamente para transparência no breakdown

### Modo Comparison

Quando `market=comparison`, o sistema calcula métricas para marketplace E black market simultaneamente, retornando campos `bm_*` adicionais para comparação lado a lado.

### Cache Strategy

- **TTL**: 300 segundos (alinhado com refresh de preços)
- **Chave**: tupla `(city, market, sort_by, sell_city)`
- **Invalidação**: Total a cada refresh de preços
- **Override de pesos**: Bypass automático do cache quando weights customizados são enviados

### Background Price Refresh

Uma asyncio task roda em loop infinito no lifespan do app:
1. Busca preços de todos os produtos na AODP API
2. Busca preços de todos os materiais únicos
3. Atualiza `AppState.prices`
4. Invalida todo o cache
5. Aguarda 300 segundos

## Cidades Suportadas

| Cidade | Bônus |
|---|---|
| Bridgewatch | Warrior, Crossbow |
| Fort Sterling | Soldier, Plate |
| Lymhurst | Hunter, Leather |
| Martlock | Mage, Cloth |
| Thetford | Gatherer, Fiber |
| Caerleon | Sem bônus (hub central) |
| Brecilien | Sem bônus |
