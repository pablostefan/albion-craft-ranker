import type {
  ItemsResponse,
  ItemDetailResponse,
  CitiesResponse,
  ConfigResponse,
  ItemsQueryParams,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    }
  }

  const res = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, `API ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

export function fetchItems(params: ItemsQueryParams = {}): Promise<ItemsResponse> {
  const query: Record<string, string> = {};
  if (params.city) query.city = params.city;
  if (params.category) query.category = params.category;
  if (params.tier !== undefined) query.tier = String(params.tier);
  if (params.enchantment !== undefined) query.enchantment = String(params.enchantment);
  if (params.quality !== undefined) query.quality = String(params.quality);
  if (params.min_profit !== undefined) query.min_profit = String(params.min_profit);
  if (params.sort_by) query.sort_by = params.sort_by;
  if (params.order) query.order = params.order;
  if (params.limit !== undefined) query.limit = String(params.limit);
  if (params.offset !== undefined) query.offset = String(params.offset);
  if (params.market) query.market = params.market;
  if (params.sell_city) query.sell_city = params.sell_city;
  if (params.w_profit !== undefined) query.w_profit = String(params.w_profit);
  if (params.w_focus !== undefined) query.w_focus = String(params.w_focus);
  if (params.w_liquidity !== undefined) query.w_liquidity = String(params.w_liquidity);
  if (params.w_freshness !== undefined) query.w_freshness = String(params.w_freshness);
  return request<ItemsResponse>("/items", query);
}

export function fetchItemDetail(
  productId: string,
  params?: { city?: string; market?: string; sell_city?: string },
): Promise<ItemDetailResponse> {
  const query: Record<string, string> = {};
  if (params?.city) query.city = params.city;
  if (params?.market) query.market = params.market;
  if (params?.sell_city) query.sell_city = params.sell_city;
  return request<ItemDetailResponse>(`/items/${encodeURIComponent(productId)}`, query);
}

export function fetchCities(): Promise<CitiesResponse> {
  return request<CitiesResponse>("/cities");
}

export function fetchConfig(): Promise<ConfigResponse> {
  return request<ConfigResponse>("/config");
}

export { ApiError };
