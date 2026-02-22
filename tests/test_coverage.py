"""
Tests for engine/coverage.py — End-to-end tests
Read docs/testing-guide.md before modifying.
"""

import pytest
from tests.conftest import load_fixture, parse_request
from engine.validator import validate
from engine import pool_builder, order_grouper
from engine.pool_builder import build
from engine.order_grouper import group
from engine import phase_a, phase_b, phase_c, coverage


def run_engine(fixture_data):
    request = parse_request(fixture_data["payload"])
    request = validate(request)
    pool = build(request.vehicles)
    groups = group(request.orders)
    a_short, a_flex, a_auto, a_cross = phase_a.run(pool, groups, request.config)
    b_short, b_flex, b_auto, b_cross = phase_b.run(pool, groups, request.config)
    c_short, c_triggered = phase_c.run(pool, a_short, b_short, a_flex, b_flex, request.config)
    return coverage.build_response(
        pool, request.orders, c_short, c_triggered,
        a_auto or b_auto, a_cross or b_cross, request.config,
    )


def test_full_coverage_own_only():
    data = load_fixture("end_to_end/full_coverage_own_only.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.own_vehicles_selected == meta["_expected_own_selected"]
    assert result.summary.subcon_vehicles_selected == meta["_expected_subcon_selected"]
    assert result.summary.auto_fallback_triggered == meta["_expected_auto_fallback_triggered"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_full_coverage_mixed_fleet():
    data = load_fixture("end_to_end/full_coverage_mixed_fleet.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_partial_coverage_weight_shortage():
    data = load_fixture("end_to_end/partial_coverage_weight_shortage.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]
    for key in meta["_expected_shortfall_keys"]:
        assert key in result.coverage.shortfall


def test_all_vehicles_unavailable():
    data = load_fixture("end_to_end/all_vehicles_unavailable.json")
    meta = data["metadata"]
    request = parse_request(data["payload"])
    request = validate(request)
    pool = build(request.vehicles)
    groups = group(request.orders)
    # With empty pool (all vehicles unavailable), phases produce shortfalls
    a_short, a_flex, a_auto, a_cross = phase_a.run(pool, groups, request.config)
    b_short, b_flex, b_auto, b_cross = phase_b.run(pool, groups, request.config)
    c_short, c_triggered = phase_c.run(pool, a_short, b_short, a_flex, b_flex, request.config)
    result = coverage.build_response(
        pool, request.orders, c_short, c_triggered,
        a_auto or b_auto, a_cross or b_cross, request.config,
    )
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.total_vehicles_selected == meta["_expected_total_selected"]


def test_no_orders():
    data = load_fixture("end_to_end/no_orders.json")
    meta = data["metadata"]
    with pytest.raises(ValueError, match=meta["_expected_error"]):
        request = parse_request(data["payload"])
        validate(request)


def test_dual_dimension_orders():
    data = load_fixture("end_to_end/dual_dimension_orders.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_vehicle_priority_both():
    data = load_fixture("end_to_end/vehicle_priority_both.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_cross_type_fallback_end_to_end():
    data = load_fixture("end_to_end/cross_type_fallback_end_to_end.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.cross_type_fallback_triggered == meta["_expected_cross_type_fallback_triggered"]
    assert result.summary.total_vehicles_selected == meta["_expected_total_selected"]


def test_large_batch_stress():
    data = load_fixture("end_to_end/large_batch_stress.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]
    assert result.summary.total_orders == 20
