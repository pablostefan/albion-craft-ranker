# Guia de Desenvolvimento

## Pré-requisitos

- Python 3.12+
- Node.js 20+
- Arquivo `data/items.json` do [ao-bin-dumps](https://github.com/ao-data/ao-bin-dumps)

## Setup

### Backend

```bash
# Criar e ativar virtual environment
python -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Baixar items.json (obrigatório)
# Copie o arquivo items.json do ao-bin-dumps para data/items.json
```

### Frontend

```bash
cd frontend
npm install
```

## Executando

### Backend (API)

```bash
# Desenvolvimento com auto-reload
uvicorn src.api.app:create_app --factory --reload --port 8000
```

O backend inicia e automaticamente:
1. Parseia `data/items.json` (9.197 receitas)
2. Busca preços na AODP API
3. Inicia refresh automático a cada 5 minutos

### Frontend

```bash
cd frontend
npm run dev
```

Acesse `http://localhost:3000`.

### CLI (modo legado)

```bash
python -m src.main --city Lymhurst --output output/ranking.csv
```

## Testes

```bash
# Todos os testes
pytest

# Com coverage
pytest --cov=src --cov-report=term-missing

# Testes específicos
pytest tests/test_scoring.py -v
pytest tests/test_api/ -v
```

124 testes cobrindo scoring engine, API endpoints e edge cases.

## Estrutura do Projeto

```
albion-craft-ranker/
├── src/
│   ├── api/
│   │   ├── app.py              # Factory, lifespan, CORS
│   │   ├── cache.py            # TTLCache (300s)
│   │   ├── dependencies.py     # AppState dataclass
│   │   ├── schemas.py          # Pydantic models
│   │   └── routes/
│   │       ├── items.py        # GET /items, GET /items/{id}
│   │       ├── cities.py       # GET /cities
│   │       └── config.py       # GET /config
│   ├── scoring.py              # Scoring engine + ScoringConfig
│   ├── recipe_parser.py        # Parse items.json → Recipe[]
│   ├── albion_client.py        # AODP API client (httpx)
│   ├── main.py                 # CLI entry point
│   └── models.py               # Recipe, MarketPrice dataclasses
├── frontend/
│   ├── app/                    # Next.js App Router pages
│   ├── components/             # React components
│   └── lib/                    # API client, utils
├── tests/
│   ├── test_scoring.py
│   ├── test_api/
│   └── conftest.py
├── data/
│   ├── items.json              # ao-bin-dumps (não versionado)
│   └── recipes.csv             # Receitas legado
├── docs/
│   ├── API.md                  # Referência da API
│   ├── ARCHITECTURE.md         # Arquitetura do sistema
│   ├── PRD.yaml                # Product Requirements Document
│   ├── design/                 # Decisões de design
│   └── plan/                   # Planos de implementação
└── output/                     # Saída do CLI
```

## Variáveis de Ambiente

Nenhuma variável de ambiente é necessária para desenvolvimento local. O backend usa valores padrão:

| Config | Padrão | Descrição |
|---|---|---|
| Host | `localhost` | Servidor local |
| Port | `8000` | Porta do backend |
| AODP URL | `https://west.albion-online-data.com` | API de preços |
| Cache TTL | `300s` | Tempo de cache |
| Premium | `true` | Taxa de venda 4% (vs 8%) |

## Convenções de Código

- **Backend**: Python com type hints, dataclasses para modelos, Pydantic para schemas de API
- **Frontend**: TypeScript strict, componentes funcionais, Tailwind CSS 4
- **Testes**: pytest, fixtures em conftest.py, mocks para API externa
- **Git**: Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`)
