# Albion Craft Ranker Component Tree

## 1. Route Map

```text
frontend/src/app
├── layout.tsx
├── page.tsx
└── items
    └── [id]
        └── page.tsx
```

## 2. App Shell Tree

```text
AppLayout
├── ThemeProvider
├── QueryStateProvider
├── AppHeader
│   ├── BrandLockup
│   ├── ServerBadge
│   ├── FreshnessIndicator
│   └── HeaderActions
└── PageContainer
```

### Ownership

- `layout.tsx` owns theme, global background, and persistent header chrome
- route pages own data fetching and route-specific composition
- search params are the shared state contract between ranking and detail routes

## 3. Ranking Page Tree

```text
RankingPage
├── DashboardControls
│   ├── BlackMarketToggle
│   ├── FilterDrawerButton
│   ├── SortSummary
│   └── RefreshButton
├── DashboardSummaryStrip
│   ├── SummaryCard(return_rate_pct_best)
│   ├── SummaryCard(profitable_count)
│   ├── SummaryCard(city_mode)
│   └── SummaryCard(stale_count)
├── DashboardLayout
│   ├── FilterSidebar
│   │   ├── CategoryFilter
│   │   ├── TierFilter
│   │   ├── EnchantmentFilter
│   │   ├── CityFilter
│   │   ├── QualityFilter
│   │   ├── MinProfitFilter
│   │   ├── WeightConfig
│   │   └── FilterActions
│   └── RankingContent
│       ├── ActiveFilterChips
│       ├── DataStateBanner
│       ├── RankingTable
│       │   ├── RankingTableHeader
│       │   ├── RankingTableBody
│       │   │   └── RankingRow
│       │   │       ├── ItemIdentityCell
│       │   │       ├── ReturnRateCell
│       │   │       ├── ProfitCell
│       │   │       ├── CityCell
│       │   │       ├── FocusCell
│       │   │       ├── LiquidityCell
│       │   │       └── ComparisonCells(optional)
│       │   └── RankingTableFooter
│       └── PaginationControls
```

## 4. Item Detail Page Tree

```text
ItemDetailPage
├── DetailBackLink
├── ItemHero
│   ├── ItemIdentityCard
│   ├── ProfitSummaryCard
│   └── FreshnessBadgeGroup
├── DetailBody
│   ├── CostBreakdown
│   │   ├── CostBreakdownHeader
│   │   ├── CostBreakdownTable
│   │   └── CostBreakdownTotals
│   ├── RevenueBreakdownCard
│   └── CityComparison
│       ├── CityComparisonChart
│       └── CityComparisonTable
└── DetailNavigation
    ├── PreviousItemLink
    └── NextItemLink
```

## 5. Component Responsibilities

| Component | Responsibility | Owner state |
|------|------|------|
| `RankingPage` | Reads URL params, fetches ranking data, composes layout | search params, loading, error |
| `BlackMarketToggle` | Switches `market` mode across 3 states | controlled by page |
| `FilterSidebar` | Collects and applies filters | draft state in drawer, committed state in URL |
| `WeightConfig` | Edits scoring weights and validates sum behavior | local draft until apply |
| `RankingTable` | Renders sortable ranking data with responsive variants | controlled sort callbacks |
| `RankingRow` | Presents row metrics and detail link | stateless |
| `ItemDetailPage` | Fetches one item payload and preserves origin query params | search params, loading, error |
| `CostBreakdown` | Shows materials, RRR effect, totals | stateless |
| `CityComparison` | Shows same item across all cities | local selected metric optional |

## 6. Suggested Props Contracts

### Ranking data model

```ts
type MarketMode = 'marketplace' | 'black_market' | 'comparison';

type RankingItem = {
  id: string;
  itemName: string;
  tier: number;
  enchantment: 0 | 1 | 2 | 3;
  category: string;
  returnRatePct: number;
  profit: number;
  bestCity: string;
  profitPerFocus: number | null;
  focusCost: number | null;
  liquidity: number | null;
  freshnessHours: number | null;
  isBlackMarketEligible: boolean;
  comparison?: {
    marketplaceProfit: number | null;
    blackMarketProfit: number | null;
    delta: number | null;
  };
};
```

### Page search params

```ts
type RankingSearchParams = {
  market?: MarketMode;
  category?: string;
  tier?: string;
  enchantment?: string;
  city?: string;
  quality?: string;
  minProfit?: string;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  weights?: string;
  page?: string;
};
```

### Component props

```ts
type BlackMarketToggleProps = {
  value: MarketMode;
  onChange: (value: MarketMode) => void;
  disabled?: boolean;
};

type FilterSidebarProps = {
  value: RankingSearchParams;
  categories: string[];
  cities: string[];
  isOpenOnMobile: boolean;
  onApply: (next: RankingSearchParams) => void;
  onReset: () => void;
  onCloseMobile: () => void;
};

type WeightConfigValue = {
  profit: number;
  focus: number;
  liquidity: number;
  freshness: number;
};

type WeightConfigProps = {
  value: WeightConfigValue;
  onChange: (next: WeightConfigValue) => void;
  onApply: () => void;
};

type RankingTableProps = {
  items: RankingItem[];
  marketMode: MarketMode;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  loading: boolean;
  onSortChange: (column: string) => void;
  buildItemHref: (itemId: string) => string;
};
```

### Detail data model

```ts
type CostBreakdownLine = {
  materialId: string;
  materialName: string;
  quantity: number;
  unitPrice: number;
  subtotal: number;
  rrrApplied: number | null;
  effectiveQuantity: number;
  isArtifactComponent: boolean;
};

type CityProfitPoint = {
  city: string;
  profit: number;
  returnRatePct: number;
  rrr: number;
  isBest: boolean;
};

type ItemDetailModel = {
  id: string;
  itemName: string;
  tier: number;
  enchantment: number;
  category: string;
  marketMode: MarketMode;
  bestCity: string;
  returnRatePct: number;
  profit: number;
  profitPerFocus: number | null;
  focusCost: number | null;
  freshnessHours: number | null;
  revenue: {
    sellPrice: number;
    setupFee: number;
    salesTax: number;
    netRevenue: number;
  };
  costs: {
    grossMaterialCost: number;
    rrrSavings: number;
    effectiveCraftCost: number;
  };
  materials: CostBreakdownLine[];
  cityComparison: CityProfitPoint[];
};
```

## 7. State Ownership and Flow

### Ranking page state flow

```text
URL search params
-> parse on server/page boundary
-> fetch ranking data
-> render summary + sidebar + table
-> user interaction updates local control state
-> apply commits back to URL
-> refetch
```

Rules:

- committed filter state lives in URL, not in disconnected component state
- drawer edits may stay local until `Apply`
- sort interactions should update URL immediately
- pagination must preserve all other params

### Detail page state flow

```text
Item id + inherited query params
-> fetch item detail payload
-> render hero and comparison
-> back link returns to original ranking URL
```

## 8. Responsive Composition Rules

| Area | Desktop | Tablet | Mobile |
|------|------|------|------|
| Sidebar | persistent left column | drawer | drawer |
| Summary strip | 4 cards in one row | 2x2 grid | horizontal snap or 2-column stack |
| Table | full columns | compact columns + scroll | compact rows or horizontal table |
| Detail hero | 2-column split | stacked cards | stacked cards |
| City comparison | chart + table | chart above table | cards/table only |

## 9. Accessibility Contracts Per Component

| Component | Required semantics |
|------|------|
| `BlackMarketToggle` | `role="radiogroup"` or segmented button pattern with labels |
| `FilterSidebar` | modal drawer uses `dialog` semantics on mobile |
| `RankingTable` | semantic `table`, `thead`, `tbody`, sortable header buttons |
| `RankingRow` | row link must expose item name and profitability summary |
| `CostBreakdown` | semantic table with footer totals |
| `CityComparison` | semantic table fallback even if chart is present |

## 10. Backend Contract Expectations for Tasks 008-010

Frontend implementation will be simpler if task 007 exposes:

1. Stable item ids and human-readable item names in ranking payloads.
2. `return_rate_pct`, `profit`, `best_city`, `profit_per_focus`, `focus_cost`, `liquidity`, and freshness metadata in list responses.
3. `marketplace` and `black_market` comparison values in one row when `market=comparison`.
4. Full revenue and cost breakdown for `GET /items/{id}`.
5. A list of available categories and cities, either from `/config` or in response metadata.

## 11. Build Sequence Recommendation

1. Task 008 should create the shell, theme tokens, typed models, and `RankingTable` with loading, empty, and error states.
2. Task 009 should layer `FilterSidebar`, `BlackMarketToggle`, and `WeightConfig` on top of URL state without rewriting the ranking table.
3. Task 010 should reuse ranking search params and shared theme tokens to keep navigation and contrast consistent.

## 12. Risks to Watch During Implementation

- If comparison mode duplicates rows instead of columns, the table becomes hard to scan and breaks the spec.
- If the backend omits freshness and comparison fields, the frontend will need placeholder states and follow-up schema work.
- If mobile uses only horizontal scroll without a compact-row fallback, profitability scanning becomes too slow.