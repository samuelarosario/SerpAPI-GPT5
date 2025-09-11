from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class FlightSearchParams(BaseModel):
    departure_id: str
    arrival_id: str
    outbound_date: str
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants_in_seat: int = 0
    infants_on_lap: int = 0
    travel_class: int = 1
    currency: str = "USD"
    deep_search: bool | None = None
    max_price: int | None = None
    include_airlines: List[str] | None = None
    exclude_airlines: List[str] | None = None

class Segment(BaseModel):
    departure_airport: str = Field(alias='departure_airport_code')
    arrival_airport: str = Field(alias='arrival_airport_code')
    departure_time: str | None = None
    arrival_time: str | None = None
    duration_minutes: int | None = None
    airline_code: str | None = None
    flight_number: str | None = None
    travel_class: str | None = None

class Layover(BaseModel):
    airport_code: str
    duration_minutes: int | None = None
    is_overnight: bool | None = None

class PriceInsights(BaseModel):
    lowest_price: int | None = None
    price_level: str | None = None
    typical_price_low: int | None = None
    typical_price_high: int | None = None

class FlightResult(BaseModel):
    result_type: str
    result_rank: int | None = None
    total_duration: int | None = None
    total_price: str | None = None
    price_currency: str | None = None
    flight_type: str | None = None
    layover_count: int | None = None
    segments: List[Segment] = []
    layovers: List[Layover] = []

class NormalizedSearch(BaseModel):
    search_id: str
    params: FlightSearchParams
    best_flights: List[FlightResult] = []
    other_flights: List[FlightResult] = []
    price_insights: PriceInsights | None = None

__all__ = [
    'FlightSearchParams','Segment','Layover','PriceInsights','FlightResult','NormalizedSearch'
]
