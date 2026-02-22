"""
Tests for engine/candidate_selector.py
Read docs/testing-guide.md before modifying.
"""

import pytest
from engine.candidate_selector import get_candidates
from engine.pool_builder import build
from models.vehicle import Vehicle, VehicleCapacity
from schemas.request import EngineConfig


def _build_pool(vehicles):
    return build(vehicles)


def test_filters_by_vehicle_type():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000)),
        Vehicle(vehicle_id="VEH-002", vehicle_type="bdouble", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=200, max_weight_kg=8000)),
    ]
    pool = _build_pool(vehicles)
    config = EngineConfig()
    candidates = get_candidates(pool, "single", "pallet", config)
    assert len(candidates) == 1
    assert candidates[0]["vehicle_id"] == "VEH-001"


def test_flexible_skips_type_check():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000)),
        Vehicle(vehicle_id="VEH-002", vehicle_type="bdouble", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=200, max_weight_kg=8000)),
    ]
    pool = _build_pool(vehicles)
    config = EngineConfig()
    candidates = get_candidates(pool, None, "pallet", config)
    assert len(candidates) == 2


def test_excludes_null_dimension():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=None)),
    ]
    pool = _build_pool(vehicles)
    config = EngineConfig()
    candidates = get_candidates(pool, "single", "weight", config)
    assert len(candidates) == 0


def test_loaded_with_rule_excludes_mismatched():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000)),
    ]
    pool = _build_pool(vehicles)
    pool["VEH-001"]["selected"] = True
    pool["VEH-001"]["loaded_with"] = "pallet"
    config = EngineConfig()
    # Should be excluded from weight candidates
    candidates = get_candidates(pool, "single", "weight", config)
    assert len(candidates) == 0
    # Should be included for pallet
    candidates = get_candidates(pool, "single", "pallet", config)
    assert len(candidates) == 1


def test_pallet_dual_sort():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000)),
        Vehicle(vehicle_id="VEH-002", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=150, max_weight_kg=3000)),
    ]
    pool = _build_pool(vehicles)
    config = EngineConfig(vehicle_priority="both")
    candidates = get_candidates(pool, "single", "pallet", config)
    # VEH-002 has higher pallet (150 > 100) → first
    assert candidates[0]["vehicle_id"] == "VEH-002"
    assert candidates[1]["vehicle_id"] == "VEH-001"


def test_weight_dual_sort():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000)),
        Vehicle(vehicle_id="VEH-002", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=150, max_weight_kg=3000)),
    ]
    pool = _build_pool(vehicles)
    config = EngineConfig(vehicle_priority="both")
    candidates = get_candidates(pool, "single", "weight", config)
    # VEH-001 has higher weight (5000 > 3000) → first
    assert candidates[0]["vehicle_id"] == "VEH-001"
    assert candidates[1]["vehicle_id"] == "VEH-002"


def test_ownership_priority_own_first():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="subcontractor",
                available=True, capacity=VehicleCapacity(max_pallet_space=200, max_weight_kg=8000)),
        Vehicle(vehicle_id="VEH-002", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000)),
    ]
    pool = _build_pool(vehicles)
    config = EngineConfig(vehicle_priority="own")
    candidates = get_candidates(pool, "single", "pallet", config)
    # Own first despite subcon having higher pallet
    assert candidates[0]["vehicle_id"] == "VEH-002"


def test_ownership_priority_subcon_first():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=200, max_weight_kg=8000)),
        Vehicle(vehicle_id="VEH-002", vehicle_type="single", type="subcontractor",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000)),
    ]
    pool = _build_pool(vehicles)
    config = EngineConfig(vehicle_priority="subcontractor")
    candidates = get_candidates(pool, "single", "pallet", config)
    assert candidates[0]["vehicle_id"] == "VEH-002"


def test_selected_vehicle_zero_remaining_excluded():
    vehicles = [
        Vehicle(vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000)),
    ]
    pool = _build_pool(vehicles)
    pool["VEH-001"]["selected"] = True
    pool["VEH-001"]["loaded_with"] = "pallet"
    pool["VEH-001"]["remaining_pallet"] = 0
    config = EngineConfig()
    candidates = get_candidates(pool, "single", "pallet", config)
    assert len(candidates) == 0
