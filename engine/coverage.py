"""
Coverage — Steps 8 and 9
==========================
Read docs/capacity-constraints.md + docs/api-contract.md before modifying.

Responsibilities:
- Determine coverage status: full / partial / none
- Build complete EngineResponse from vehicle_pool and shortfalls
- Calculate total_demand from all orders
- Calculate total_capacity_selected from selected vehicles
- Build summary counts and flags

Coverage status rules:
  none    → no vehicles selected at all
  full    → phase_C_shortfalls is empty
  partial → phase_C_shortfalls has entries

Shortfall key format:
  "{vehicle_type}_{dimension}"  for typed orders  e.g. "single_weight"
  "flexible_{dimension}"        for flexible       e.g. "flexible_pallet"
"""

from typing import Dict, Any, List
from models.order import Order
from schemas.response import (
    EngineResponse, SelectedVehicle, OriginalCapacity, RemainingCapacity,
    Coverage, TotalDemand, TotalCapacitySelected, Summary,
)
from schemas.request import EngineConfig


def build_response(
    vehicle_pool: Dict[str, Any],
    orders: List[Order],
    phase_C_shortfalls: Dict[str, float],
    phase_C_triggered: bool,
    auto_fallback_triggered: bool,
    cross_type_fallback_triggered: bool,
    config: EngineConfig
) -> EngineResponse:
    """
    Builds the final EngineResponse.
    Determines coverage status from shortfalls.
    Assembles selected vehicles, coverage, and summary blocks.
    """
    # Build selected_vehicles list
    selected_vehicles = []
    for v in vehicle_pool.values():
        if not v["selected"]:
            continue
        selected_vehicles.append(SelectedVehicle(
            vehicle_id=v["vehicle_id"],
            vehicle_type=v["vehicle_type"],
            ownership_type=v["ownership_type"],
            loaded_with=v["loaded_with"],
            selected_phase=v["selected_phase"],
            original_capacity=OriginalCapacity(
                max_pallet_space=v["max_pallet_space"],
                max_weight_kg=v["max_weight_kg"],
            ),
            remaining_capacity=RemainingCapacity(
                pallet=v["remaining_pallet"],
                weight=v["remaining_weight"],
            ),
        ))

    # Determine coverage status
    if not selected_vehicles:
        status = "none"
    elif phase_C_shortfalls:
        status = "partial"
    else:
        status = "full"

    # Calculate total demand
    total_pallet_demand = sum(
        o.capacity_required.pallet_space
        for o in orders
        if o.capacity_required.pallet_space is not None
    )
    total_weight_demand = sum(
        o.capacity_required.weight_kg
        for o in orders
        if o.capacity_required.weight_kg is not None
    )

    # Calculate total capacity selected — only count dimension matching loaded_with
    total_pallet_selected = sum(
        v["max_pallet_space"]
        for v in vehicle_pool.values()
        if v["selected"] and v["loaded_with"] == "pallet" and v["max_pallet_space"] is not None
    )
    total_weight_selected = sum(
        v["max_weight_kg"]
        for v in vehicle_pool.values()
        if v["selected"] and v["loaded_with"] == "weight" and v["max_weight_kg"] is not None
    )

    coverage = Coverage(
        status=status,
        total_demand=TotalDemand(
            pallet_space=total_pallet_demand if total_pallet_demand > 0 else None,
            weight_kg=total_weight_demand if total_weight_demand > 0 else None,
        ),
        total_capacity_selected=TotalCapacitySelected(
            pallet_space=total_pallet_selected if total_pallet_selected > 0 else None,
            weight_kg=total_weight_selected if total_weight_selected > 0 else None,
        ),
        shortfall=phase_C_shortfalls if phase_C_shortfalls else None,
    )

    # Build summary
    pallet_count = sum(
        1 for o in orders if o.high_dimension_preference == "pallet_space"
    )
    weight_count = sum(
        1 for o in orders if o.high_dimension_preference == "weight_kg"
    )
    flexible_count = sum(
        1 for o in orders if o.vehicle_type_required is None
    )
    vehicle_types_in_batch = sorted(set(
        v["vehicle_type"] for v in vehicle_pool.values()
    ))
    own_selected = sum(
        1 for v in vehicle_pool.values()
        if v["selected"] and v["ownership_type"] == "own"
    )
    subcon_selected = sum(
        1 for v in vehicle_pool.values()
        if v["selected"] and v["ownership_type"] == "subcontractor"
    )

    summary = Summary(
        total_orders=len(orders),
        pallet_orders_count=pallet_count,
        weight_orders_count=weight_count,
        flexible_orders_count=flexible_count,
        vehicle_types_in_batch=vehicle_types_in_batch,
        own_vehicles_selected=own_selected,
        subcon_vehicles_selected=subcon_selected,
        total_vehicles_selected=own_selected + subcon_selected,
        auto_fallback_triggered=auto_fallback_triggered,
        cross_type_fallback_triggered=cross_type_fallback_triggered,
        phase_c_triggered=phase_C_triggered,
    )

    return EngineResponse(
        selected_vehicles=selected_vehicles,
        coverage=coverage,
        summary=summary,
    )
