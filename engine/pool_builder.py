"""
Pool Builder — Step 2
======================
Read docs/capacity-constraints.md before modifying.

Responsibilities:
- Filter out unavailable vehicles (available=false)
- Build mutable vehicle pool dict keyed by vehicle_id
- Initialise remaining_pallet = max_pallet_space
- Initialise remaining_weight = max_weight_kg
- Set loaded_with = null, selected = false, selected_phase = null

Vehicle pool is shared and mutated across all phases.
Capacity deducted in Phase A carries forward into Phase B and C.
"""

from typing import Dict, Any, List
from models.vehicle import Vehicle


def build(vehicles: List[Vehicle]) -> Dict[str, Any]:
    """
    Builds mutable vehicle pool from vehicle list.
    Excludes unavailable vehicles.
    Returns dict keyed by vehicle_id.
    """
    pool = {}
    for v in vehicles:
        if not v.available:
            continue
        pool[v.vehicle_id] = {
            "vehicle_id": v.vehicle_id,
            "vehicle_type": v.vehicle_type,
            "ownership_type": v.type,
            "max_pallet_space": v.capacity.max_pallet_space,
            "max_weight_kg": v.capacity.max_weight_kg,
            "remaining_pallet": v.capacity.max_pallet_space,
            "remaining_weight": v.capacity.max_weight_kg,
            "loaded_with": None,
            "selected": False,
            "selected_phase": None,
        }
    return pool
