"""
Response Schema
================
Read docs/api-contract.md before modifying.

EngineResponse is the full output payload:
  selected_vehicles     — vehicles chosen to cover demand
  coverage              — status, demand totals, shortfall
  summary               — counts and flags
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Literal


class OriginalCapacity(BaseModel):
    max_pallet_space: Optional[float] = None
    max_weight_kg: Optional[float] = None


class RemainingCapacity(BaseModel):
    pallet: Optional[float] = None
    weight: Optional[float] = None


class SelectedVehicle(BaseModel):
    vehicle_id: str
    vehicle_type: str
    ownership_type: str
    loaded_with: Literal["pallet", "weight"]
    selected_phase: Literal["A", "B", "C"]
    original_capacity: OriginalCapacity
    remaining_capacity: RemainingCapacity


class TotalDemand(BaseModel):
    pallet_space: Optional[float] = None
    weight_kg: Optional[float] = None


class TotalCapacitySelected(BaseModel):
    pallet_space: Optional[float] = None
    weight_kg: Optional[float] = None


class Coverage(BaseModel):
    status: Literal["full", "partial", "none"]
    total_demand: TotalDemand
    total_capacity_selected: TotalCapacitySelected
    shortfall: Optional[Dict[str, float]] = None
    # shortfall key format: "{vehicle_type}_{dimension}" or "flexible_{dimension}"


class Summary(BaseModel):
    total_orders: int
    pallet_orders_count: int
    weight_orders_count: int
    flexible_orders_count: int
    vehicle_types_in_batch: List[str]
    own_vehicles_selected: int
    subcon_vehicles_selected: int
    total_vehicles_selected: int
    auto_fallback_triggered: bool
    cross_type_fallback_triggered: bool
    phase_c_triggered: bool


class EngineResponse(BaseModel):
    selected_vehicles: List[SelectedVehicle]
    coverage: Coverage
    summary: Summary
