/** TypeScript interfaces matching FastAPI Pydantic schemas (src/api/schemas.py). */

export interface ScoredItem {
  product_id: string;
  craft_city: string;
  sell_mode: string;
  material_cost: number;
  effective_craft_cost: number;
  setup_fee: number;
  sales_tax: number;
  sell_price: number;
  net_revenue: number;
  profit_absolute: number;
  return_rate_pct: number;
  focus_cost: number;
  profit_per_focus: number;
  freshness_score: number;
  liquidity_score: number;
  best_city: string;
  final_score: number;
  bm_sell_price: number | null;
  bm_net_revenue: number | null;
  bm_profit: number | null;
  bm_return_rate_pct: number | null;
}

export interface ItemsResponse {
  items: ScoredItem[];
  total: number;
  filters_applied: Record<string, string | number | null>;
}

export interface MaterialCost {
  item_id: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  is_artifact_component: boolean;
}

export interface CityComparison {
  city: string;
  return_rate_pct: number | null;
  profit_absolute: number | null;
  sell_price: number | null;
}

export interface ItemDetailResponse {
  item: ScoredItem;
  cost_breakdown: MaterialCost[];
  city_comparison: CityComparison[];
}

export interface CityBonusSchema {
  category: string;
  bonus_pct: number;
}

export interface CitySchema {
  name: string;
  bonuses: CityBonusSchema[];
}

export interface CitiesResponse {
  cities: CitySchema[];
}

export interface ConfigResponse {
  setup_fee_rate: number;
  premium_tax_rate: number;
  normal_tax_rate: number;
  is_premium: boolean;
  profit_weight: number;
  focus_weight: number;
  liquidity_weight: number;
  freshness_weight: number;
  min_profit: number;
  sales_tax_rate: number;
}

export type SortField =
  | "final_score"
  | "return_rate_pct"
  | "profit"
  | "profit_per_focus"
  | "liquidity";

export type SortOrder = "asc" | "desc";

export type MarketMode = "marketplace" | "black_market" | "comparison";

export interface ItemsQueryParams {
  city?: string;
  category?: string;
  tier?: number;
  enchantment?: number;
  quality?: number;
  min_profit?: number;
  sort_by?: SortField;
  order?: SortOrder;
  limit?: number;
  offset?: number;
  market?: MarketMode;
  sell_city?: string;
  w_profit?: number;
  w_focus?: number;
  w_liquidity?: number;
  w_freshness?: number;
  exclude_cities?: string;
  use_focus?: boolean;
}
