from dataclasses import dataclass
from datetime import date

@dataclass
class SearchConfig:
    origin: str
    window_start: date
    window_end: date
    min_nights: int
    max_nights: int
    destination_mode: str = "all"
    currency: str = "EUR"