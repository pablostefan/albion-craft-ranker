from __future__ import annotations

import asyncio
from collections import deque
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Deque, Dict, Iterable, List, Sequence

import httpx


BASE_URLS = {
    "west": "https://west.albion-online-data.com",
    "east": "https://east.albion-online-data.com",
    "europe": "https://europe.albion-online-data.com",
}

ALL_CITY_LOCATIONS = (
    "Bridgewatch",
    "Fort Sterling",
    "Lymhurst",
    "Martlock",
    "Thetford",
    "Caerleon",
    "Brecilien",
    "Arthur's Rest",
    "Morgana's Rest",
)

# PRD-aligned city set (7 cities): matches rrr_engine.SUPPORTED_CITIES.
# Used as the default for get_prices_all_cities() so integration tasks reason
# about a stable, RRR-compatible city model. ALL_CITY_LOCATIONS remains
# available for raw/broader queries (e.g. Black Market, hideouts).
PRD_CITY_LOCATIONS: tuple[str, ...] = (
    "Bridgewatch",
    "Fort Sterling",
    "Lymhurst",
    "Martlock",
    "Thetford",
    "Caerleon",
    "Brecilien",
)

USER_AGENT = "albion-craft-ranker/2.0"


@dataclass
class MarketPrice:
    item_id: str
    city: str
    quality: int
    sell_price_min: float
    buy_price_max: float
    sell_price_min_date: str
    buy_price_max_date: str
    now_provider: Callable[[], datetime] = field(
        default=lambda: datetime.now(timezone.utc),
        repr=False,
        compare=False,
    )

    @property
    def staleness_hours(self) -> float:
        timestamps = [
            parsed
            for parsed in (
                self._parse_timestamp(self.sell_price_min_date),
                self._parse_timestamp(self.buy_price_max_date),
            )
            if parsed is not None
        ]
        if not timestamps:
            return 0.0

        latest_timestamp = max(timestamps)
        delta = self.now_provider() - latest_timestamp
        return round(max(delta.total_seconds(), 0.0) / 3600.0, 3)

    @staticmethod
    def _parse_timestamp(value: str) -> datetime | None:
        cleaned = value.strip()
        if not cleaned:
            return None

        normalized = cleaned.replace("Z", "+00:00")
        if "T" not in normalized and " " in normalized:
            normalized = normalized.replace(" ", "T", 1)

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


class AlbionAPIClient:
    def __init__(
        self,
        server: str = "west",
        timeout: int = 30,
        http_client: httpx.Client | None = None,
        sleep_func: Callable[[float], None] = time.sleep,
        monotonic_func: Callable[[], float] = time.monotonic,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        if server not in BASE_URLS:
            raise ValueError(f"Servidor invalido: {server}. Use west, east ou europe.")
        self.base_url = BASE_URLS[server]
        self.timeout = timeout
        self._sleep = sleep_func
        self._monotonic = monotonic_func
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
        )
        self._request_timestamps: Deque[float] = deque()

    def close(self) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def _get_json(self, path: str, params: Dict[str, str], retries: int = 5) -> List[dict]:
        url = f"{self.base_url}{path}"

        for attempt in range(retries + 1):
            self._respect_rate_limits()
            try:
                response = self._http_client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                return payload if isinstance(payload, list) else []
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < retries:
                    retry_after = exc.response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else 5.0 * (2 ** attempt)
                    self._sleep(wait)
                    continue
                raise
            except httpx.RequestError:
                if attempt < retries:
                    self._sleep(1.0 * (2 ** attempt))
                    continue
                raise

        return []

    def _respect_rate_limits(self) -> None:
        while True:
            now = self._monotonic()
            self._prune_request_timestamps(now)

            last_minute = [timestamp for timestamp in self._request_timestamps if now - timestamp < 60.0]
            last_five_minutes = [timestamp for timestamp in self._request_timestamps if now - timestamp < 300.0]

            waits: List[float] = []
            if len(last_minute) >= 180:
                waits.append(60.0 - (now - last_minute[0]))
            if len(last_five_minutes) >= 300:
                waits.append(300.0 - (now - last_five_minutes[0]))

            if not waits:
                self._request_timestamps.append(now)
                return

            wait_for = max(max(waits), 0.0)
            if wait_for > 0:
                self._sleep(wait_for)

    def _prune_request_timestamps(self, now: float) -> None:
        while self._request_timestamps and now - self._request_timestamps[0] >= 300.0:
            self._request_timestamps.popleft()

    @staticmethod
    def _unique_values(values: Iterable[str]) -> List[str]:
        unique: List[str] = []
        seen = set()
        for value in values:
            normalized = str(value).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(normalized)
        return unique

    def get_prices(self, item_ids: Iterable[str], locations: Iterable[str], quality: int) -> List[MarketPrice]:
        unique_ids = self._unique_values(item_ids)
        locations_str = ",".join(self._unique_values(locations))
        if not unique_ids or not locations_str:
            return []

        # Batch into chunks to avoid URL-too-long errors and API rate limits.
        # Smaller chunks (50) with a small inter-chunk delay prevents 429s.
        batch_size = 50
        out: List[MarketPrice] = []
        for i in range(0, len(unique_ids), batch_size):
            chunk = unique_ids[i : i + batch_size]
            item_ids_str = ",".join(chunk)
            if i > 0:
                self._sleep(0.5)
            rows = self._get_json(
                f"/api/v2/stats/prices/{item_ids_str}.json",
                {
                    "locations": locations_str,
                    "qualities": str(quality),
                },
            )

            for row in rows:
                out.append(
                    MarketPrice(
                        item_id=str(row.get("item_id", "")),
                        city=str(row.get("city", "")),
                        quality=int(row.get("quality", quality) or quality),
                        sell_price_min=float(row.get("sell_price_min", 0) or 0),
                        buy_price_max=float(row.get("buy_price_max", 0) or 0),
                        sell_price_min_date=str(row.get("sell_price_min_date", "")),
                        buy_price_max_date=str(row.get("buy_price_max_date", "")),
                        now_provider=self._now_provider,
                    )
                )
        return out

    def get_prices_all_cities(
        self,
        item_ids: Iterable[str],
        quality: int,
        locations: Sequence[str] | None = None,
    ) -> List[MarketPrice]:
        return self.get_prices(item_ids, locations or PRD_CITY_LOCATIONS, quality)

    async def get_prices_async(
        self,
        item_ids: Iterable[str],
        locations: Iterable[str],
        quality: int,
        max_concurrent: int = 5,
    ) -> List[MarketPrice]:
        """Async concurrent version of get_prices.

        Sends up to ``max_concurrent`` batch requests in parallel, which
        reduces total fetch time from O(batches) to O(batches/concurrency).
        """
        unique_ids = self._unique_values(item_ids)
        locations_str = ",".join(self._unique_values(locations))
        if not unique_ids or not locations_str:
            return []

        batch_size = 50
        batches = [
            unique_ids[i : i + batch_size] for i in range(0, len(unique_ids), batch_size)
        ]
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_batch(chunk: List[str]) -> List[MarketPrice]:
            async with semaphore:
                item_ids_str = ",".join(chunk)
                url = f"{self.base_url}/api/v2/stats/prices/{item_ids_str}.json"
                params = {"locations": locations_str, "qualities": str(quality)}
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                ) as client:
                    for attempt in range(5):
                        try:
                            response = await client.get(url, params=params)
                            response.raise_for_status()
                            rows = response.json()
                            return [
                                MarketPrice(
                                    item_id=str(row.get("item_id", "")),
                                    city=str(row.get("city", "")),
                                    quality=int(row.get("quality", quality) or quality),
                                    sell_price_min=float(row.get("sell_price_min", 0) or 0),
                                    buy_price_max=float(row.get("buy_price_max", 0) or 0),
                                    sell_price_min_date=str(row.get("sell_price_min_date", "")),
                                    buy_price_max_date=str(row.get("buy_price_max_date", "")),
                                    now_provider=self._now_provider,
                                )
                                for row in (rows if isinstance(rows, list) else [])
                            ]
                        except httpx.HTTPStatusError as exc:
                            if exc.response.status_code == 429 and attempt < 4:
                                retry_after = exc.response.headers.get("Retry-After")
                                wait = float(retry_after) if retry_after and retry_after.isdigit() else 5.0 * (2**attempt)
                                await asyncio.sleep(wait)
                                continue
                            raise
                        except httpx.RequestError:
                            if attempt < 4:
                                await asyncio.sleep(1.0 * (2**attempt))
                                continue
                            raise
                return []

        all_results = await asyncio.gather(*[fetch_batch(b) for b in batches], return_exceptions=True)
        out: List[MarketPrice] = []
        for result in all_results:
            if isinstance(result, list):
                out.extend(result)
        return out

    def get_history_bulk(
        self,
        item_ids: Iterable[str],
        location: str,
        quality: int,
        days: int = 7,
    ) -> Dict[str, List[dict]]:
        ids = sorted(set(item_ids))
        if not ids:
            return {}

        end = date.today()
        start = end - timedelta(days=days)

        rows = self._get_json(
            f"/api/v2/stats/history/{','.join(ids)}.json",
            {
                "date": start.isoformat(),
                "end_date": end.isoformat(),
                "locations": location,
                "qualities": str(quality),
                "time-scale": "24",
            },
        )

        grouped: Dict[str, List[dict]] = {i: [] for i in ids}
        for row in rows if isinstance(rows, list) else []:
            item_id = str(row.get("item_id", "")).strip()
            if item_id:
                grouped.setdefault(item_id, []).append(row)

        return grouped
