"""
Candidate Selector — Step 4 (get_candidates helper)
=====================================================
Read docs/vehicle-selection.md before modifying.

Responsibilities:
- Filter eligible vehicles from pool based on:
    * loaded_with rule (selected vehicles must match dimension)
    * vehicle_type match (null = flexible = skip type check)
    * must have required dimension capacity defined (not null)
    * remaining capacity > 0 for selected vehicles
- Apply Option A dual sort:
    pallet dimension → pallet_space DESC, weight_kg ASC
    weight dimension → weight_kg DESC, pallet_space ASC
- Apply ownership priority as STABLE sort on top:
    "own"           → own first, subcon second
    "subcontractor" → subcon first, own second
    "both"          → no ownership re-sort (dual sort is final)

STABLE sort is critical — preserves dual sort order within each group.

The loaded_with rule is the most important rule:
  loaded_with="pallet" → vehicle only offered for pallet dimension
  loaded_with="weight" → vehicle only offered for weight dimension
  loaded_with=null     → vehicle not yet selected, both dimensions available
"""

from typing import Dict, Any, List, Optional
from schemas.request import EngineConfig


def get_candidates(
    vehicle_pool: Dict[str, Any],
    vehicle_type: Optional[str],
    dimension: str,
    config: EngineConfig
) -> List[Dict[str, Any]]:
    """
    Returns sorted list of eligible vehicles for the given dimension.

    Args:
        vehicle_pool: mutable vehicle pool from pool_builder
        vehicle_type: required vehicle type, None = any type (flexible)
        dimension: "pallet" or "weight"
        config: engine config for ownership priority

    Returns:
        Sorted list of eligible vehicle dicts
    """
    candidates = []

    for v in vehicle_pool.values():
        # Vehicle type match (skip check for flexible orders where vehicle_type is None)
        if vehicle_type is not None and v["vehicle_type"] != vehicle_type:
            continue

        # Must have the required dimension capacity defined (not null)
        if dimension == "pallet" and v["max_pallet_space"] is None:
            continue
        if dimension == "weight" and v["max_weight_kg"] is None:
            continue

        # loaded_with rule
        if v["selected"]:
            # Already selected — loaded_with must match dimension
            if dimension == "pallet" and v["loaded_with"] != "pallet":
                continue
            if dimension == "weight" and v["loaded_with"] != "weight":
                continue
            # Remaining capacity must be > 0
            if dimension == "pallet" and (v["remaining_pallet"] is None or v["remaining_pallet"] <= 0):
                continue
            if dimension == "weight" and (v["remaining_weight"] is None or v["remaining_weight"] <= 0):
                continue

        candidates.append(v)

    # Option A dual sort
    if dimension == "pallet":
        # PRIMARY: pallet_space DESC, SECONDARY: weight_kg ASC
        candidates.sort(
            key=lambda v: (
                -(v["remaining_pallet"] if v["remaining_pallet"] is not None else 0),
                v["remaining_weight"] if v["remaining_weight"] is not None else float("inf"),
            )
        )
    else:
        # PRIMARY: weight_kg DESC, SECONDARY: pallet_space ASC
        candidates.sort(
            key=lambda v: (
                -(v["remaining_weight"] if v["remaining_weight"] is not None else 0),
                v["remaining_pallet"] if v["remaining_pallet"] is not None else float("inf"),
            )
        )

    # Ownership priority — stable sort on top
    if config.vehicle_priority == "own":
        candidates.sort(key=lambda v: 0 if v["ownership_type"] == "own" else 1)
    elif config.vehicle_priority == "subcontractor":
        candidates.sort(key=lambda v: 0 if v["ownership_type"] == "subcontractor" else 1)
    # "both" — no ownership re-sort

    return candidates
