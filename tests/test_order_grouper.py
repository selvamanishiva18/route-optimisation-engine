"""
Tests for engine/order_grouper.py
Read docs/testing-guide.md before modifying.
"""

import pytest
from models.order import Order, CapacityRequired
from engine.order_grouper import group


def test_typed_pallet_grouped():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="single",
            high_dimension_preference="pallet_space",
            capacity_required=CapacityRequired(pallet_space=80),
        ),
        Order(
            order_id="ORD-002", vehicle_type_required="single",
            high_dimension_preference="pallet_space",
            capacity_required=CapacityRequired(pallet_space=60),
        ),
    ]
    groups = group(orders)
    assert "single" in groups.typed_pallet_groups
    assert len(groups.typed_pallet_groups["single"]) == 2


def test_typed_weight_grouped():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required="bdouble",
            high_dimension_preference="weight_kg",
            capacity_required=CapacityRequired(weight_kg=3000),
        ),
    ]
    groups = group(orders)
    assert "bdouble" in groups.typed_weight_groups
    assert len(groups.typed_weight_groups["bdouble"]) == 1


def test_flexible_pallet():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required=None,
            high_dimension_preference="pallet_space",
            capacity_required=CapacityRequired(pallet_space=40),
        ),
    ]
    groups = group(orders)
    assert len(groups.flexible_pallet_orders) == 1
    assert len(groups.typed_pallet_groups) == 0


def test_flexible_weight():
    orders = [
        Order(
            order_id="ORD-001", vehicle_type_required=None,
            high_dimension_preference="weight_kg",
            capacity_required=CapacityRequired(weight_kg=1000),
        ),
    ]
    groups = group(orders)
    assert len(groups.flexible_weight_orders) == 1


def test_mixed_orders_grouped_correctly():
    orders = [
        Order(order_id="ORD-001", vehicle_type_required="single",
              high_dimension_preference="pallet_space",
              capacity_required=CapacityRequired(pallet_space=80)),
        Order(order_id="ORD-002", vehicle_type_required="bdouble",
              high_dimension_preference="weight_kg",
              capacity_required=CapacityRequired(weight_kg=3000)),
        Order(order_id="ORD-003", vehicle_type_required=None,
              high_dimension_preference="pallet_space",
              capacity_required=CapacityRequired(pallet_space=40)),
        Order(order_id="ORD-004", vehicle_type_required=None,
              high_dimension_preference="weight_kg",
              capacity_required=CapacityRequired(weight_kg=500)),
    ]
    groups = group(orders)
    assert len(groups.typed_pallet_groups["single"]) == 1
    assert len(groups.typed_weight_groups["bdouble"]) == 1
    assert len(groups.flexible_pallet_orders) == 1
    assert len(groups.flexible_weight_orders) == 1
