"""
Phase B — Weight Preference Orders (Step 6)
============================================
Read docs/vehicle-selection.md + docs/capacity-constraints.md before modifying.

Responsibilities:
- Process all orders where high_dimension_preference = "weight_kg"
- vehicle_pool carries forward from Phase A with reduced remaining capacity
- Vehicles with loaded_with="pallet" are COMPLETELY EXCLUDED
  (physical rule — pallet-loaded vehicles cannot accept weight orders)
- For each typed sub-group:
    * get_candidates for that vehicle type + weight dimension
    * cross-type fallback if configured
    * greedily assign using MIN deduction formula
    * mark vehicle: selected=true, loaded_with="weight", selected_phase="B"
    * if vehicle already selected (loaded_with="weight") — only update capacity
- For flexible weight orders:
    * Priority 1: already selected vehicles with loaded_with="weight" + remaining_weight > 0
    * Priority 2: unselected vehicles of same types as already selected
    * If unfulfilled → phase_B_flexible_unfulfilled

CRITICAL: loaded_with="pallet" vehicles must never appear in Phase B candidates.

Returns:
    phase_B_shortfalls: Dict[str, float]   { vehicle_type: unmet_weight_amount }
    phase_B_flexible_unfulfilled: float
"""

from typing import Dict, Any, Tuple
from engine.order_grouper import OrderGroups
from engine.candidate_selector import get_candidates
from engine.phase_a import _process_demand, _assign_from_candidates, _get_selected_vehicle_types
from schemas.request import EngineConfig


def run(
    vehicle_pool: Dict[str, Any],
    order_groups: OrderGroups,
    config: EngineConfig
) -> Tuple[Dict[str, float], float, bool, bool]:
    """
    Runs Phase B — weight preference processing.
    Mutates vehicle_pool in place.

    Returns:
        (phase_B_shortfalls, phase_B_flexible_unfulfilled,
         auto_fallback_triggered, cross_type_fallback_triggered)
    """
    shortfalls = {}
    cross_type_flags = []
    auto_fallback_flags = []

    # Process typed weight sub-groups
    for vtype, orders in order_groups.typed_weight_groups.items():
        demand = sum(o.capacity_required.weight_kg for o in orders)
        remaining = _process_demand(
            vehicle_pool, demand, vtype, "weight", "B", config,
            cross_type_flags, auto_fallback_flags,
        )
        if remaining > 0:
            shortfalls[f"{vtype}_weight"] = remaining

    # Process flexible weight orders
    flexible_demand = sum(
        o.capacity_required.weight_kg for o in order_groups.flexible_weight_orders
    )
    flexible_unfulfilled = 0.0

    if flexible_demand > 0:
        remaining = flexible_demand

        # Priority 1: already selected weight-loaded vehicles with remaining capacity
        selected_candidates = get_candidates(vehicle_pool, None, "weight", config)
        selected_only = [c for c in selected_candidates if c["selected"]]
        remaining = _assign_from_candidates(selected_only, remaining, "weight", "B")

        # Priority 2: unselected vehicles of same types as already selected for weight
        if remaining > 0:
            selected_types = _get_selected_vehicle_types(vehicle_pool, "weight")
            unselected_candidates = get_candidates(vehicle_pool, None, "weight", config)
            unselected_only = [
                c for c in unselected_candidates
                if not c["selected"] and c["vehicle_type"] in selected_types
            ]

            if not config.auto_fallback_to_leased and config.vehicle_priority in ("own", "subcontractor"):
                preferred = config.vehicle_priority
                unselected_only = [c for c in unselected_only if c["ownership_type"] == preferred]

            remaining = _assign_from_candidates(unselected_only, remaining, "weight", "B")

        if remaining > 0:
            flexible_unfulfilled = remaining

    return shortfalls, flexible_unfulfilled, bool(auto_fallback_flags), bool(cross_type_flags)
