"""
Phase A — Pallet Preference Orders (Step 5)
============================================
Read docs/vehicle-selection.md + docs/capacity-constraints.md before modifying.

Responsibilities:
- Process all orders where high_dimension_preference = "pallet_space"
- For each typed sub-group (e.g. "single", "bdouble"):
    * get_candidates for that vehicle type + pallet dimension
    * if no candidates and allow_cross_type_fallback=true → retry any type
    * if no candidates at all → add to phase_A_shortfalls
    * greedily assign using MIN deduction formula
    * mark vehicle: selected=true, loaded_with="pallet", selected_phase="A"
- For flexible pallet orders:
    * Priority 1: already selected vehicles with remaining_pallet > 0
    * Priority 2: unselected vehicles of same types as already selected
    * If unfulfilled → phase_A_flexible_unfulfilled

Returns:
    phase_A_shortfalls: Dict[str, float]   { vehicle_type: unmet_pallet_amount }
    phase_A_flexible_unfulfilled: float
"""

from typing import Dict, Any, Tuple, Set
from engine.order_grouper import OrderGroups
from engine.candidate_selector import get_candidates
from schemas.request import EngineConfig


def _get_ownership_filtered_candidates(
    vehicle_pool: Dict[str, Any],
    vehicle_type,
    dimension: str,
    config: EngineConfig,
) -> list:
    """Get candidates filtered by ownership rules."""
    candidates = get_candidates(vehicle_pool, vehicle_type, dimension, config)

    if not config.auto_fallback_to_leased and config.vehicle_priority in ("own", "subcontractor"):
        preferred = config.vehicle_priority
        return [c for c in candidates if c["ownership_type"] == preferred]

    return candidates


def _process_demand(
    vehicle_pool: Dict[str, Any],
    demand: float,
    vehicle_type,
    dimension: str,
    phase: str,
    config: EngineConfig,
    cross_type_fallback_triggered: list,
    auto_fallback_triggered: list,
) -> float:
    """
    Greedy assignment loop. Returns remaining unfulfilled demand.
    """
    remaining = demand
    candidates = get_candidates(vehicle_pool, vehicle_type, dimension, config)

    # If no candidates and cross-type fallback enabled, retry with any type
    if not candidates and vehicle_type is not None and config.allow_cross_type_fallback:
        candidates = get_candidates(vehicle_pool, None, dimension, config)
        if candidates:
            cross_type_fallback_triggered.append(True)

    if config.vehicle_priority in ("own", "subcontractor") and config.auto_fallback_to_leased:
        preferred = config.vehicle_priority
        preferred_candidates = [c for c in candidates if c["ownership_type"] == preferred]
        remaining = _assign_from_candidates(preferred_candidates, remaining, dimension, phase)
        if remaining > 0:
            fallback_candidates = [c for c in candidates if c["ownership_type"] != preferred]
            if fallback_candidates:
                auto_fallback_triggered.append(True)
            remaining = _assign_from_candidates(fallback_candidates, remaining, dimension, phase)
    elif not config.auto_fallback_to_leased and config.vehicle_priority in ("own", "subcontractor"):
        preferred = config.vehicle_priority
        filtered = [c for c in candidates if c["ownership_type"] == preferred]
        remaining = _assign_from_candidates(filtered, remaining, dimension, phase)
    else:
        remaining = _assign_from_candidates(candidates, remaining, dimension, phase)

    return remaining


def _assign_from_candidates(
    candidates: list,
    remaining: float,
    dimension: str,
    phase: str,
) -> float:
    """Assign demand to candidates greedily. Returns remaining demand."""
    dim_remaining_key = "remaining_pallet" if dimension == "pallet" else "remaining_weight"
    loaded_with_value = "pallet" if dimension == "pallet" else "weight"

    for v in candidates:
        if remaining <= 0:
            break

        available = v[dim_remaining_key]
        if available is None or available <= 0:
            continue

        deduct = min(available, remaining)
        v[dim_remaining_key] -= deduct
        remaining -= deduct

        if not v["selected"]:
            v["selected"] = True
            v["loaded_with"] = loaded_with_value
            v["selected_phase"] = phase

    return remaining


def _get_selected_vehicle_types(vehicle_pool: Dict[str, Any], dimension: str) -> Set[str]:
    """Get the set of vehicle types that have been selected for the given dimension."""
    loaded_with_value = "pallet" if dimension == "pallet" else "weight"
    return {
        v["vehicle_type"] for v in vehicle_pool.values()
        if v["selected"] and v["loaded_with"] == loaded_with_value
    }


def run(
    vehicle_pool: Dict[str, Any],
    order_groups: OrderGroups,
    config: EngineConfig
) -> Tuple[Dict[str, float], float, bool, bool]:
    """
    Runs Phase A — pallet preference processing.
    Mutates vehicle_pool in place.

    Returns:
        (phase_A_shortfalls, phase_A_flexible_unfulfilled,
         auto_fallback_triggered, cross_type_fallback_triggered)
    """
    shortfalls = {}
    cross_type_flags = []
    auto_fallback_flags = []

    # Process typed pallet sub-groups
    for vtype, orders in order_groups.typed_pallet_groups.items():
        demand = sum(o.capacity_required.pallet_space for o in orders)
        remaining = _process_demand(
            vehicle_pool, demand, vtype, "pallet", "A", config,
            cross_type_flags, auto_fallback_flags,
        )
        if remaining > 0:
            shortfalls[f"{vtype}_pallet"] = remaining

    # Process flexible pallet orders
    flexible_demand = sum(
        o.capacity_required.pallet_space for o in order_groups.flexible_pallet_orders
    )
    flexible_unfulfilled = 0.0

    if flexible_demand > 0:
        remaining = flexible_demand

        # Priority 1: already selected pallet-loaded vehicles with remaining capacity
        selected_candidates = get_candidates(vehicle_pool, None, "pallet", config)
        selected_only = [c for c in selected_candidates if c["selected"]]
        remaining = _assign_from_candidates(selected_only, remaining, "pallet", "A")

        # Priority 2: unselected vehicles of same types as already selected
        if remaining > 0:
            selected_types = _get_selected_vehicle_types(vehicle_pool, "pallet")
            unselected_candidates = get_candidates(vehicle_pool, None, "pallet", config)
            unselected_only = [
                c for c in unselected_candidates
                if not c["selected"] and c["vehicle_type"] in selected_types
            ]

            if not config.auto_fallback_to_leased and config.vehicle_priority in ("own", "subcontractor"):
                preferred = config.vehicle_priority
                unselected_only = [c for c in unselected_only if c["ownership_type"] == preferred]

            remaining = _assign_from_candidates(unselected_only, remaining, "pallet", "A")

        if remaining > 0:
            flexible_unfulfilled = remaining

    return shortfalls, flexible_unfulfilled, bool(auto_fallback_flags), bool(cross_type_flags)
