"""
Tests for engine/phase_c.py
Read docs/testing-guide.md before modifying.
"""

import pytest
from tests.conftest import load_fixture, parse_request
from engine.validator import validate
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


def test_typed_pallet_resolved_by_selected_vehicle():
    data = load_fixture("phase_c/typed_pallet_resolved_by_selected_vehicle.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_typed_weight_resolved_by_new_vehicle():
    data = load_fixture("phase_c/typed_weight_resolved_by_new_vehicle.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_flexible_pallet_any_type_used():
    data = load_fixture("phase_c/flexible_pallet_any_type_used.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_flexible_weight_loaded_with_respected():
    data = load_fixture("phase_c/flexible_weight_loaded_with_respected.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_threshold_own_skipped_subcon_used():
    data = load_fixture("phase_c/threshold_own_skipped_subcon_used.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]
    assert result.summary.subcon_vehicles_selected >= meta["_expected_subcon_selected"]


def test_threshold_own_above_threshold_used():
    data = load_fixture("phase_c/threshold_own_above_threshold_used.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]
    assert result.summary.own_vehicles_selected == meta["_expected_own_selected"]
    assert result.summary.subcon_vehicles_selected == meta["_expected_subcon_selected"]


def test_all_shortfalls_unresolvable():
    data = load_fixture("phase_c/all_shortfalls_unresolvable.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]
    for key in meta["_expected_shortfall_keys"]:
        assert key in result.coverage.shortfall
