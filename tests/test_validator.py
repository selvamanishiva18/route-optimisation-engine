"""
Tests for engine/validator.py
Read docs/testing-guide.md before modifying.
"""

import pytest
from tests.conftest import load_fixture, parse_request
from engine.validator import validate
from models.order import Order, CapacityRequired
from models.vehicle import Vehicle, VehicleCapacity
from schemas.request import EngineRequest, EngineConfig


def _make_request(orders=None, vehicles=None, config=None):
    if config is None:
        config = EngineConfig()
    if vehicles is None:
        vehicles = [
            Vehicle(
                vehicle_id="VEH-001", vehicle_type="single", type="own",
                available=True, capacity=VehicleCapacity(max_pallet_space=100, max_weight_kg=5000),
            )
        ]
    if orders is None:
        orders = [
            Order(
                order_id="ORD-001", vehicle_type_required="single",
                capacity_required=CapacityRequired(pallet_space=50),
            )
        ]
    return EngineRequest(config=config, orders=orders, vehicles=vehicles)


def test_empty_orders_rejected():
    req = _make_request(orders=[])
    with pytest.raises(ValueError, match="No orders provided"):
        validate(req)


def test_empty_vehicles_rejected():
    req = _make_request(vehicles=[])
    with pytest.raises(ValueError, match="No vehicles provided"):
        validate(req)


def test_no_capacity_defined_rejected():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            capacity_required=CapacityRequired(pallet_space=None, weight_kg=None),
        )
    ]
    req = _make_request(orders=orders)
    with pytest.raises(ValueError, match="has no capacity defined"):
        validate(req)


def test_negative_pallet_rejected():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            capacity_required=CapacityRequired(pallet_space=-10),
        )
    ]
    req = _make_request(orders=orders)
    with pytest.raises(ValueError, match="has negative capacity value"):
        validate(req)


def test_negative_weight_rejected():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            capacity_required=CapacityRequired(weight_kg=-5),
        )
    ]
    req = _make_request(orders=orders)
    with pytest.raises(ValueError, match="has negative capacity value"):
        validate(req)


def test_zero_converted_to_null():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            capacity_required=CapacityRequired(pallet_space=50, weight_kg=0),
        )
    ]
    req = _make_request(orders=orders)
    result = validate(req)
    assert result.orders[0].capacity_required.weight_kg is None


def test_auto_set_pallet_preference():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            capacity_required=CapacityRequired(pallet_space=50),
        )
    ]
    req = _make_request(orders=orders)
    result = validate(req)
    assert result.orders[0].high_dimension_preference == "pallet_space"


def test_auto_set_weight_preference():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            capacity_required=CapacityRequired(weight_kg=1000),
        )
    ]
    req = _make_request(orders=orders)
    result = validate(req)
    assert result.orders[0].high_dimension_preference == "weight_kg"


def test_dual_dimension_missing_preference_rejected():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            capacity_required=CapacityRequired(pallet_space=50, weight_kg=1000),
        )
    ]
    req = _make_request(orders=orders)
    with pytest.raises(ValueError, match="high_dimension_preference mandatory"):
        validate(req)


def test_preference_mismatch_rejected():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            high_dimension_preference="pallet_space",
            capacity_required=CapacityRequired(weight_kg=1000),
        )
    ]
    req = _make_request(orders=orders)
    with pytest.raises(ValueError, match="prefers pallet_space but value is null"):
        validate(req)


def test_duplicate_order_id_rejected():
    orders = [
        Order(order_id="ORD-001", capacity_required=CapacityRequired(pallet_space=50)),
        Order(order_id="ORD-001", capacity_required=CapacityRequired(pallet_space=30)),
    ]
    req = _make_request(orders=orders)
    with pytest.raises(ValueError, match="Duplicate order ID"):
        validate(req)


def test_duplicate_vehicle_id_rejected():
    vehicles = [
        Vehicle(
            vehicle_id="VEH-001", vehicle_type="single", type="own",
            available=True, capacity=VehicleCapacity(max_pallet_space=100),
        ),
        Vehicle(
            vehicle_id="VEH-001", vehicle_type="single", type="own",
            available=True, capacity=VehicleCapacity(max_pallet_space=100),
        ),
    ]
    req = _make_request(vehicles=vehicles)
    with pytest.raises(ValueError, match="Duplicate vehicle ID"):
        validate(req)


def test_all_vehicles_unavailable_passes_validation():
    """All vehicles unavailable is not a validation error — engine returns status=none."""
    vehicles = [
        Vehicle(
            vehicle_id="VEH-001", vehicle_type="single", type="own",
            available=False, capacity=VehicleCapacity(max_pallet_space=100),
        ),
    ]
    req = _make_request(vehicles=vehicles)
    result = validate(req)
    assert result is not None


def test_valid_request_passes():
    req = _make_request()
    result = validate(req)
    assert result is not None
