# Albion Craft Ranker

Descubra os itens mais lucrativos para craftar no Albion Online. O projeto ranqueia **3.900+ itens craftáveis** cruzando preços em tempo real, bonus de cidade, Resource Return Rate (RRR) dinâmico e otimização por foco.

**Stack:** FastAPI (backend) · Next.js 15 (frontend) · Albion Online Data Project API

## Features

- **return_rate_pct** como métrica primária de lucro / custo total em %
- **RRR dinâmico** por cidade/categoria/foco (não hardcoded)
- **9.197 receitas** parseadas automaticamente do `items.json` (ao-bin-dumps)
- **Otimização cross-city** encontra a melhor cidade para cada item
- **Black Market** modo marketplace, black_market ou comparison lado a lado
- **Profit per Focus** fórmula delta: (lucro_com_foco - lucro_sem_foco) / custo_foco
- **Pesos configuráveis** profit, focus, liquidity, freshness com normalização automática
- **Filtros** categoria, tier, encantamento, cidade, qualidade, lucro mínimo
- **Detalhes do item** breakdown de materiais + comparação entre 7 cidades
- **CLI v2** para uso headless / scripts

## Quick Start

### Pré-requisitos

- Python 3.12+
- Node.js 20+
- `items.json` do [ao-bin-dumps](https://github.com/ao-data/ao-bin-dumps) em `data/`

### 1. Backend

```bash
pip install -r requirements.txt
cp /caminho/para/ao-bin-dumps/items.json data/items.json
uvicorn src.api.app:create_app --factory --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# Abrir http://localhost:3000
```

### 3. CLI (opcional)

```bash
# Ranking v2 com items.json
python3 -m src.main \
  --items-json data/items.json \
  --craft-city Lymhurst \
  --sell-mode marketplace \
  --premium \
  --top 20

# Modo legado com CSV
python3 -m src.main \
  --recipes data/recipes.csv \
  --craft-city Bridgewatch \
  --sell-city Caerleon \
  --top 20
```

## Estrutura do Projeto

```
├── src/                    # Backend Python
│   ├── main.py             # CLI v2 (--items-json / --recipes)
│   ├── models.py           # Dataclasses: Recipe, ScoredItem, ScoringConfig
│   ├── recipe_parser.py    # items.json → list[Recipe]
│   ├── rrr_engine.py       # RRR dinâmico por cidade/categoria
│   ├── albion_client.py    # HTTP client (AODP API, 7+2 cidades)
│   ├── scoring.py          # Scoring Engine v2 (rank_items_v2)
│   └── api/                # FastAPI app
│       ├── app.py          # Factory + lifespan + CORS
│       ├── schemas.py      # Pydantic request/response
│       ├── cache.py        # TTL cache + background refresh
│       └── routes/         # GET /items, /items/{id}, /cities, /config
├── frontend/               # Next.js 15 + Tailwind
│   └── src/
│       ├── app/            # App Router pages
│       ├── components/     # RankingTable, FilterSidebar, WeightConfig...
│       └── lib/            # API client, types, formatters
├── tests/                  # pytest (124 testes)
├── docs/                   # PRD, design specs, planos
└── data/                   # items.json, recipes.csv
```

## Documentação

- [API Reference](docs/API.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Desenvolvimento](docs/DEVELOPMENT.md)

## Configuração

| Variável de Ambiente | Padrão | Descrição |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL da API para o frontend |

### Parâmetros do CLI

| Flag | Padrão | Descrição |
|---|---|---|
| `--items-json` | - | Caminho do items.json (modo v2) |
| `--recipes` | - | Caminho do CSV (modo legado) |
| `--craft-city` | **obrigatório** | Cidade de craft |
| `--sell-city` | = craft-city | Cidade de venda |
| `--sell-mode` | `marketplace` | marketplace / black_market / comparison |
| `--premium` / `--no-premium` | `--premium` | Status premium (4% vs 8% tax) |
| `--use-focus` | `false` | Calcular profit_per_focus |
| `--best-city` | `false` | Otimizar cidade para cada item |
| `--top` | `20` | Número de itens no ranking |

## Fórmulas

- `RRR = 1 - 1 / (1 + ProductionBonus / 100)`
- `effective_craft_cost = material_cost * (1 - RRR)`
- `setup_fee = effective_craft_cost * 2.5%`
- `sales_tax = sell_price * 4% (premium) ou 8% (normal)`
- `net_revenue = sell_price - sales_tax`
- `profit = net_revenue - effective_craft_cost - setup_fee`
- `return_rate_pct = (profit / (effective_craft_cost + setup_fee)) * 100`
- `profit_per_focus = (profit_com_foco - profit_sem_foco) / focus_cost`

## Licença

Uso pessoal. Dados providos pelo [Albion Online Data Project](https://www.albion-online-data.com/).
