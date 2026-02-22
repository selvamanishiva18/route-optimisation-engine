"""
Tests for engine/pool_builder.py
Read docs/testing-guide.md before modifying.
"""

import pytest
from models.vehicle import Vehicle, VehicleCapacity
from engine.pool_builder import build


def test_excludes_unavailable_vehicles():
    vehicles = [
        Vehicle(
            vehicle_id="VEH-001", vehicle_type="single", type="own",
            available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000),
        ),
        Vehicle(
            vehicle_id="VEH-002", vehicle_type="single", type="own",
            available=False, capacity=VehicleCapacity(max_pallet_space=80, max_weight_kg=3000),
        ),
    ]
    pool = build(vehicles)
    assert "VEH-001" in pool
    assert "VEH-002" not in pool


def test_initialises_remaining_capacity():
    vehicles = [
        Vehicle(
            vehicle_id="VEH-001", vehicle_type="single", type="own",
            available=True, capacity=VehicleCapacity(max_pallet_space=150, max_weight_kg=5000),
        ),
    ]
    pool = build(vehicles)
    v = pool["VEH-001"]
    assert v["remaining_pallet"] == 150
    assert v["remaining_weight"] == 5000


def test_initialises_selection_state():
    vehicles = [
        Vehicle(
            vehicle_id="VEH-001", vehicle_type="single", type="own",
            available=True, capacity=VehicleCapacity(max_pallet_space=100),
        ),
    ]
    pool = build(vehicles)
    v = pool["VEH-001"]
    assert v["loaded_with"] is None
    assert v["selected"] is False
    assert v["selected_phase"] is None


def test_preserves_null_dimensions():
    vehicles = [
        Vehicle(
            vehicle_id="VEH-001", vehicle_type="single", type="own",
            available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=None),
        ),
    ]
    pool = build(vehicles)
    v = pool["VEH-001"]
    assert v["max_weight_kg"] is None
    assert v["remaining_weight"] is None


def test_empty_vehicles_returns_empty_pool():
    pool = build([])
    assert pool == {}
