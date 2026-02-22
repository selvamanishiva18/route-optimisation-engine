"""
Vehicle Models
===============
Read docs/vehicle-selection.md before modifying.

Key rules:
- vehicle_type is dynamic — never hardcoded in engine logic
- type must be "own" or "subcontractor"
- available=false means completely excluded from selection
- cost_per_trip reserved for Phase 5 — unused in Phase 1
- max_pallet_space=null means vehicle cannot serve pallet orders
- max_weight_kg=null means vehicle cannot serve weight orders
"""

from pydantic import BaseModel
from typing import Optional, Literal


class VehicleCapacity(BaseModel):
    max_pallet_space: Optional[float] = None
    max_weight_kg: Optional[float] = None


class Vehicle(BaseModel):
    vehicle_id: str
    vehicle_type: str                          # dynamic — "single", "bdouble", etc.
    type: Literal["own", "subcontractor"]
    available: bool
    cost_per_trip: Optional[float] = None      # reserved Phase 5
    capacity: VehicleCapacity
