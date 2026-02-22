"""
Order Models
=============
Read docs/capacity-constraints.md before modifying.

Key rules:
- pallet_space and weight_kg are both optional but at least one must be non-null
- 0 is treated same as null (converted in validator)
- high_dimension_preference auto-set for single-dimension orders
- high_dimension_preference mandatory when both dimensions are non-null
- vehicle_type_required = null means flexible (any vehicle type)
"""

from pydantic import BaseModel
from typing import Optional, Literal


class CapacityRequired(BaseModel):
    pallet_space: Optional[float] = None
    weight_kg: Optional[float] = None


class Order(BaseModel):
    order_id: str
    vehicle_type_required: Optional[str] = None
    high_dimension_preference: Optional[Literal["pallet_space", "weight_kg"]] = None
    capacity_required: CapacityRequired
