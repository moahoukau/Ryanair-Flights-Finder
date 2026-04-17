import csv
from typing import Iterable

from models.trip_result import TripResult

def save_results_to_csv(results: Iterable[TripResult], filename: str) -> None:
    fieldnames = [
        "destination",
        "airport",
        "departure_date",
        "return_date",
        "nights",
        "total_price_eur",
        "outbound_flight",
        "inbound_flight",
        "outbound_departure",
        "inbound_departure",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result.as_dict())