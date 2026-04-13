from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
import unittest

import httpx

from src.albion_client import ALL_CITY_LOCATIONS, PRD_CITY_LOCATIONS, AlbionAPIClient, MarketPrice


class FakeClock:
    def __init__(self, monotonic_start: float, now_value: datetime) -> None:
        self.current = monotonic_start
        self.now_value = now_value
        self.sleep_calls: list[float] = []

    def monotonic(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.current += seconds

    def now(self) -> datetime:
        return self.now_value


class AlbionAPIClientTests(unittest.TestCase):
    def test_get_prices_supports_black_market_and_keeps_legacy_signature(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/v2/stats/prices/T4_BAG.json")
            self.assertEqual(request.url.params["locations"], "Black Market")
            self.assertEqual(request.url.params["qualities"], "1")
            return httpx.Response(
                200,
                json=[
                    {
                        "item_id": "T4_BAG",
                        "city": "Black Market",
                        "quality": 1,
                        "sell_price_min": 0,
                        "buy_price_max": 123456,
                        "sell_price_min_date": "2026-04-12T09:00:00",
                        "buy_price_max_date": "2026-04-12T11:00:00",
                    }
                ],
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(http_client.close)

        client = AlbionAPIClient(server="west", http_client=http_client)

        prices = client.get_prices(["T4_BAG"], ["Black Market"], 1)

        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0].city, "Black Market")
        self.assertEqual(prices[0].buy_price_max, 123456.0)

    def test_get_prices_all_cities_returns_rows_for_all_default_locations(self) -> None:
        """Default city set must be PRD_CITY_LOCATIONS (7 cities), not the broader ALL_CITY_LOCATIONS."""

        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.params["locations"], ",".join(PRD_CITY_LOCATIONS))
            payload = []
            for location in PRD_CITY_LOCATIONS:
                payload.append(
                    {
                        "item_id": "T4_BAG",
                        "city": location,
                        "quality": 2,
                        "sell_price_min": 1000,
                        "buy_price_max": 900,
                        "sell_price_min_date": "2026-04-12T09:00:00",
                        "buy_price_max_date": "2026-04-12T10:00:00",
                    }
                )
            return httpx.Response(200, json=payload)

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(http_client.close)

        client = AlbionAPIClient(server="west", http_client=http_client)

        prices = client.get_prices_all_cities(["T4_BAG"], quality=2)

        self.assertEqual(len(prices), len(PRD_CITY_LOCATIONS))
        self.assertEqual({price.city for price in prices}, set(PRD_CITY_LOCATIONS))

    def test_prd_city_locations_matches_rrr_engine_supported_cities(self) -> None:
        """Contract test: PRD_CITY_LOCATIONS must stay in sync with rrr_engine.SUPPORTED_CITIES.

        If this fails, either albion_client or rrr_engine was updated without updating the other.
        """
        from src.rrr_engine import SUPPORTED_CITIES  # noqa: PLC0415

        self.assertEqual(
            set(PRD_CITY_LOCATIONS),
            set(SUPPORTED_CITIES),
            "PRD_CITY_LOCATIONS and rrr_engine.SUPPORTED_CITIES have drifted apart.",
        )

    def test_all_city_locations_is_superset_of_prd_locations(self) -> None:
        """ALL_CITY_LOCATIONS must remain a strict superset so raw queries still reach hideouts."""
        self.assertTrue(
            set(PRD_CITY_LOCATIONS).issubset(set(ALL_CITY_LOCATIONS)),
            "PRD_CITY_LOCATIONS contains cities absent from ALL_CITY_LOCATIONS.",
        )
        self.assertGreater(
            len(ALL_CITY_LOCATIONS),
            len(PRD_CITY_LOCATIONS),
            "ALL_CITY_LOCATIONS should have more entries than PRD_CITY_LOCATIONS.",
        )

    def test_market_price_exposes_staleness_hours(self) -> None:
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc)
        price = MarketPrice(
            item_id="T4_BAG",
            city="Caerleon",
            quality=1,
            sell_price_min=1000,
            buy_price_max=900,
            sell_price_min_date="2026-04-12T08:00:00",
            buy_price_max_date="2026-04-12T09:00:00",
            now_provider=lambda: fixed_now,
        )

        self.assertEqual(price.staleness_hours, 3.0)

    def test_rate_limit_pacing_waits_when_minute_window_is_full(self) -> None:
        clock = FakeClock(
            monotonic_start=59.0,
            now_value=datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc),
        )

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=[
                    {
                        "item_id": "T4_BAG",
                        "city": "Caerleon",
                        "quality": 1,
                        "sell_price_min": 1000,
                        "buy_price_max": 900,
                        "sell_price_min_date": "2026-04-12T09:00:00",
                        "buy_price_max_date": "2026-04-12T10:00:00",
                    }
                ],
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(http_client.close)

        client = AlbionAPIClient(
            server="west",
            http_client=http_client,
            sleep_func=clock.sleep,
            monotonic_func=clock.monotonic,
            now_provider=clock.now,
        )
        client._request_timestamps = deque([0.0] * 180)

        prices = client.get_prices(["T4_BAG"], ["Caerleon"], 1)

        self.assertEqual(len(prices), 1)
        self.assertEqual(clock.sleep_calls, [1.0])


if __name__ == "__main__":
    unittest.main()