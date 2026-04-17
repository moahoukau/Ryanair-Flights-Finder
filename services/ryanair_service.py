from datetime import date, timedelta
from typing import Callable, Optional

from ryanair import Ryanair

from config.destinations import SEA_DESTINATIONS
from models.trip_result import TripResult
from models.search_config import SearchConfig


ProgressCallback = Optional[Callable[[str], None]]


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def get_all_destinations(
    origin: str,
    window_start: date,
    window_end: date,
    currency: str = "EUR",
    progress_callback: ProgressCallback = None,
    api: Ryanair | None = None,
) -> dict[str, str]:

    local_api = api or Ryanair(currency=currency)

    if progress_callback:
        progress_callback("Loading all destinations from API...")

    flights = local_api.get_cheapest_flights(origin, window_start, window_end)

    destinations: dict[str, str] = {}
    for flight in flights:
        code = getattr(flight, "destination", None)
        full_name = getattr(flight, "destinationFull", None) or code

        if code:
            destinations[full_name] = code

    if progress_callback:
        progress_callback(f"Loaded {len(destinations)} destinations.")

    return dict(sorted(destinations.items(), key=lambda item: item[0].lower()))


def get_destinations_for_mode(
    config: SearchConfig,
    api: Ryanair,
    progress_callback: ProgressCallback = None,
) -> dict[str, str]:
    if config.destination_mode == "sea":
        if progress_callback:
            progress_callback(f"Using sea destinations list ({len(SEA_DESTINATIONS)} cities).")
        return SEA_DESTINATIONS.copy()

    return get_all_destinations(
        origin=config.origin,
        window_start=config.window_start,
        window_end=config.window_end,
        currency=config.currency,
        progress_callback=progress_callback,
        api=api,
    )


def search_trips(
    config: SearchConfig,
    progress_callback: ProgressCallback = None,
) -> list[TripResult]:

    api = Ryanair(currency=config.currency)

    destinations = get_destinations_for_mode(
        config=config,
        api=api,
        progress_callback=progress_callback,
    )

    code_to_name = {code: name for name, code in destinations.items()}

    results: list[TripResult] = []
    seen: set[tuple] = set()

    for dep_date in daterange(config.window_start, config.window_end):
        for nights in range(config.min_nights, config.max_nights + 1):
            ret_date = dep_date + timedelta(days=nights)

            if ret_date > config.window_end:
                continue

            if progress_callback:
                progress_callback(
                    f"Checking {dep_date.isoformat()} -> {ret_date.isoformat()} ({nights} nights)..."
                )

            try:
                trips = api.get_cheapest_return_flights(
                    config.origin,
                    dep_date,
                    dep_date,
                    ret_date,
                    ret_date,
                )
            except Exception as e:
                if progress_callback:
                    progress_callback(
                        f"Skipped {dep_date.isoformat()} + {nights}: {e}"
                    )
                continue

            for trip in trips:
                outbound = trip.outbound
                inbound = trip.inbound

                destination_code = getattr(outbound, "destination", None)
                inbound_origin = getattr(inbound, "origin", None)

                if destination_code not in code_to_name:
                    continue

                if inbound_origin != destination_code:
                    continue

                key = (
                    destination_code,
                    dep_date.isoformat(),
                    ret_date.isoformat(),
                    getattr(outbound, "flightNumber", ""),
                    getattr(inbound, "flightNumber", ""),
                    float(getattr(trip, "totalPrice", 0.0)),
                )

                if key in seen:
                    continue

                seen.add(key)

                results.append(
                    TripResult(
                        destination=code_to_name[destination_code],
                        airport=destination_code,
                        departure_date=dep_date.isoformat(),
                        return_date=ret_date.isoformat(),
                        nights=nights,
                        total_price_eur=float(getattr(trip, "totalPrice", 0.0)),
                        outbound_flight=str(getattr(outbound, "flightNumber", "")),
                        inbound_flight=str(getattr(inbound, "flightNumber", "")),
                        outbound_departure=str(getattr(outbound, "departureTime", "")),
                        inbound_departure=str(getattr(inbound, "departureTime", "")),
                    )
                )

    results.sort(key=lambda x: x.total_price_eur)

    if progress_callback:
        progress_callback(f"Done. Found {len(results)} options.")

    return results