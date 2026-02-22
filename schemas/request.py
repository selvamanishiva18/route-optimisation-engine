"""
Request Schema
===============
Read docs/api-contract.md before modifying.

EngineRequest is the full input payload:
  config  — behaviour rules
  orders  — what needs to be shipped
  vehicles — what is available
"""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from models.order import Order
from models.vehicle import Vehicle


class EngineConfig(BaseModel):
    vehicle_priority: Literal["own", "subcontractor", "both"] = "own"
    auto_fallback_to_leased: bool = False
    own_vehicle_selection: Literal["fewest"] = "fewest"          # Phase 2 will expand
    subcontractor_selection: Literal["fewest"] = "fewest"        # Phase 2 will expand
    allow_cross_type_fallback: bool = False
    phase_c_own_utilisation_threshold: int = Field(default=50, ge=0, le=100)


class EngineRequest(BaseModel):
    config: EngineConfig
    orders: List[Order]
    vehicles: List[Vehicle]
