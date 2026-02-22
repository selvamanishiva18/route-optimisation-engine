"""
Phase C — Leftover Mixing (Step 7)
====================================
Read docs/vehicle-selection.md + docs/capacity-constraints.md before modifying.

Responsibilities:
- Collect all shortfalls from Phase A and Phase B including flexible unfulfilled
- For each shortfall:

    PRIORITY 1 — Already selected vehicles:
      * loaded_with must match dimension (physical rule — no exceptions)
      * vehicle_type must match (skip for flexible orders)
      * remaining capacity > 0
      * threshold check if vehicle_priority="both" AND vehicle is own:
          threshold = vehicle.max_[dim] * (phase_c_own_utilisation_threshold / 100)
          if leftover < threshold → SKIP own vehicle (subcon will handle)
      * Applies Option D: threshold calculated per candidate vehicle

    PRIORITY 2 — Unselected vehicles:
      * same type match (skip for flexible)
      * cross-type fallback if allow_cross_type_fallback=true
      * same threshold check for own vehicles when priority="both"
      * mark selected=true, loaded_with=dimension, selected_phase="C"

loaded_with rule summary for Phase C:
  Typed pallet  → same vehicle_type + loaded_with="pallet"
  Typed weight  → same vehicle_type + loaded_with="weight"
  Flexible pallet → any vehicle_type + loaded_with="pallet"
  Flexible weight → any vehicle_type + loaded_with="weight"

Returns:
    phase_C_shortfalls: Dict[str, float]  { "type_dimension": amount }
    phase_C_triggered: bool
"""

from typing import Dict, Any, Tuple
from schemas.request import EngineConfig
from engine.candidate_selector import get_candidates


def _passes_threshold(vehicle: Dict[str, Any], leftover: float, dimension: str, config: EngineConfig) -> bool:
    """Check if this vehicle passes the Phase C threshold check."""
    if config.vehicle_priority != "both":
        return True
    if vehicle["ownership_type"] != "own":
        return True

    max_key = "max_pallet_space" if dimension == "pallet" else "max_weight_kg"
    max_val = vehicle[max_key]
    if max_val is None or max_val == 0:
        return True

    threshold = max_val * (config.phase_c_own_utilisation_threshold / 100)
    return leftover >= threshold


def _filter_by_ownership(candidates: list, config: EngineConfig) -> list:
    """Filter candidates by ownership rules (same as Phase A/B)."""
    if not config.auto_fallback_to_leased and config.vehicle_priority in ("own", "subcontractor"):
        preferred = config.vehicle_priority
        return [c for c in candidates if c["ownership_type"] == preferred]
    return candidates


def _resolve_shortfall(
    vehicle_pool: Dict[str, Any],
    leftover: float,
    vehicle_type,
    dimension: str,
    config: EngineConfig,
    cross_type_flags: list,
    auto_fallback_flags: list,
) -> float:
    """Try to resolve a shortfall. Returns remaining unfulfilled amount."""
    remaining = leftover
    dim_remaining_key = "remaining_pallet" if dimension == "pallet" else "remaining_weight"
    loaded_with_value = "pallet" if dimension == "pallet" else "weight"

    # PRIORITY 1: Already selected vehicles (same loaded_with, same type)
    candidates = get_candidates(vehicle_pool, vehicle_type, dimension, config)
    selected = [c for c in candidates if c["selected"]]

    # Apply ownership filtering for Priority 1 as well
    if config.vehicle_priority in ("own", "subcontractor") and config.auto_fallback_to_leased:
        preferred = config.vehicle_priority
        preferred_selected = [c for c in selected if c["ownership_type"] == preferred]
        remaining = _assign_selected(preferred_selected, remaining, dim_remaining_key, dimension, config)
        if remaining > 0:
            fallback_selected = [c for c in selected if c["ownership_type"] != preferred]
            if fallback_selected:
                auto_fallback_flags.append(True)
            remaining = _assign_selected(fallback_selected, remaining, dim_remaining_key, dimension, config)
    elif not config.auto_fallback_to_leased and config.vehicle_priority in ("own", "subcontractor"):
        preferred = config.vehicle_priority
        filtered_selected = [c for c in selected if c["ownership_type"] == preferred]
        remaining = _assign_selected(filtered_selected, remaining, dim_remaining_key, dimension, config)
    else:
        remaining = _assign_selected(selected, remaining, dim_remaining_key, dimension, config)

    if remaining <= 0:
        return 0.0

    # PRIORITY 2: Unselected vehicles
    candidates = get_candidates(vehicle_pool, vehicle_type, dimension, config)
    unselected = [c for c in candidates if not c["selected"]]

    if config.vehicle_priority in ("own", "subcontractor") and config.auto_fallback_to_leased:
        preferred = config.vehicle_priority
        preferred_unselected = [c for c in unselected if c["ownership_type"] == preferred]
        remaining = _assign_unselected(preferred_unselected, remaining, dim_remaining_key, loaded_with_value, dimension, config)
        if remaining > 0:
            fallback_unselected = [c for c in unselected if c["ownership_type"] != preferred]
            if fallback_unselected:
                auto_fallback_flags.append(True)
            remaining = _assign_unselected(fallback_unselected, remaining, dim_remaining_key, loaded_with_value, dimension, config)
    elif not config.auto_fallback_to_leased and config.vehicle_priority in ("own", "subcontractor"):
        preferred = config.vehicle_priority
        filtered_unselected = [c for c in unselected if c["ownership_type"] == preferred]
        remaining = _assign_unselected(filtered_unselected, remaining, dim_remaining_key, loaded_with_value, dimension, config)
    else:
        remaining = _assign_unselected(unselected, remaining, dim_remaining_key, loaded_with_value, dimension, config)

    # Cross-type fallback for unresolved typed shortfalls
    if remaining > 0 and vehicle_type is not None and config.allow_cross_type_fallback:
        any_candidates = get_candidates(vehicle_pool, None, dimension, config)
        any_candidates = _filter_by_ownership(any_candidates, config)

        any_selected = [c for c in any_candidates if c["selected"]]
        for v in any_selected:
            if remaining <= 0:
                break
            available = v[dim_remaining_key]
            if available is None or available <= 0:
                continue
            if not _passes_threshold(v, remaining, dimension, config):
                continue
            deduct = min(available, remaining)
            v[dim_remaining_key] -= deduct
            remaining -= deduct
            cross_type_flags.append(True)

        if remaining > 0:
            any_unselected = [c for c in any_candidates if not c["selected"]]
            for v in any_unselected:
                if remaining <= 0:
                    break
                available = v[dim_remaining_key]
                if available is None or available <= 0:
                    continue
                if not _passes_threshold(v, remaining, dimension, config):
                    continue
                deduct = min(available, remaining)
                v[dim_remaining_key] -= deduct
                remaining -= deduct
                v["selected"] = True
                v["loaded_with"] = loaded_with_value
                v["selected_phase"] = "C"
                cross_type_flags.append(True)

    return remaining


def _assign_selected(candidates, remaining, dim_remaining_key, dimension, config):
    """Assign from selected vehicles with threshold check."""
    for v in candidates:
        if remaining <= 0:
            break
        available = v[dim_remaining_key]
        if available is None or available <= 0:
            continue
        if not _passes_threshold(v, remaining, dimension, config):
            continue
        deduct = min(available, remaining)
        v[dim_remaining_key] -= deduct
        remaining -= deduct
    return remaining


def _assign_unselected(candidates, remaining, dim_remaining_key, loaded_with_value, dimension, config):
    """Assign from unselected vehicles with threshold check."""
    for v in candidates:
        if remaining <= 0:
            break
        available = v[dim_remaining_key]
        if available is None or available <= 0:
            continue
        if not _passes_threshold(v, remaining, dimension, config):
            continue
        deduct = min(available, remaining)
        v[dim_remaining_key] -= deduct
        remaining -= deduct
        v["selected"] = True
        v["loaded_with"] = loaded_with_value
        v["selected_phase"] = "C"
    return remaining


def run(
    vehicle_pool: Dict[str, Any],
    phase_A_shortfalls: Dict[str, float],
    phase_B_shortfalls: Dict[str, float],
    phase_A_flexible_unfulfilled: float,
    phase_B_flexible_unfulfilled: float,
    config: EngineConfig
) -> Tuple[Dict[str, float], bool]:
    """
    Runs Phase C — leftover mixing.
    Mutates vehicle_pool in place.

    Returns:
        (phase_C_shortfalls, phase_C_triggered)
    """
    all_shortfalls = {}
    all_shortfalls.update(phase_A_shortfalls)
    all_shortfalls.update(phase_B_shortfalls)

    if phase_A_flexible_unfulfilled > 0:
        all_shortfalls["flexible_pallet"] = phase_A_flexible_unfulfilled
    if phase_B_flexible_unfulfilled > 0:
        all_shortfalls["flexible_weight"] = phase_B_flexible_unfulfilled

    if not all_shortfalls:
        return {}, False

    phase_c_triggered = True
    final_shortfalls = {}
    cross_type_flags = []
    auto_fallback_flags = []

    for key, amount in all_shortfalls.items():
        if key.startswith("flexible_"):
            vehicle_type = None
            dimension = key.replace("flexible_", "")
        else:
            parts = key.rsplit("_", 1)
            vehicle_type = parts[0]
            dimension = parts[1]

        remaining = _resolve_shortfall(
            vehicle_pool, amount, vehicle_type, dimension, config,
            cross_type_flags, auto_fallback_flags,
        )

        if remaining > 0:
            final_shortfalls[key] = remaining

    return final_shortfalls, phase_c_triggered
