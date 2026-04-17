from dataclasses import dataclass

@dataclass
class TripResult:
    destination: str
    airport: str
    departure_date: str
    return_date: str
    nights: int
    total_price_eur: float
    outbound_flight: str
    inbound_flight: str
    outbound_departure: str
    inbound_departure: str

    def as_dict(self) -> dict:
        return {
            "destination": self.destination,
            "airport": self.airport,
            "departure_date": self.departure_date,
            "return_date": self.return_date,
            "nights": self.nights,
            "total_price_eur": self.total_price_eur,
            "outbound_flight": self.outbound_flight,
            "inbound_flight": self.inbound_flight,
            "outbound_departure": self.outbound_departure,
            "inbound_departure": self.inbound_departure,
        }