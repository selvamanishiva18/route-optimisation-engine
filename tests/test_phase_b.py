"""
Tests for engine/phase_b.py
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


def test_weight_own_covers_fully():
    data = load_fixture("phase_b/weight_own_covers_fully.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.own_vehicles_selected == meta["_expected_own_selected"]
    assert result.summary.subcon_vehicles_selected == meta["_expected_subcon_selected"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_weight_pallet_locked_vehicles_excluded():
    data = load_fixture("phase_b/weight_pallet_locked_vehicles_excluded.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.own_vehicles_selected == meta["_expected_own_selected"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_weight_subcon_fallback():
    data = load_fixture("phase_b/weight_subcon_fallback.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.own_vehicles_selected == meta["_expected_own_selected"]
    assert result.summary.subcon_vehicles_selected == meta["_expected_subcon_selected"]
    assert result.summary.auto_fallback_triggered == meta["_expected_auto_fallback_triggered"]


def test_flexible_weight_gap_fill():
    data = load_fixture("phase_b/flexible_weight_gap_fill.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    assert result.summary.total_vehicles_selected == meta["_expected_total_selected"]
    assert result.summary.phase_c_triggered == meta["_expected_phase_c_triggered"]


def test_weight_shortfall_no_fallback():
    data = load_fixture("phase_b/weight_shortfall_no_fallback.json")
    meta = data["metadata"]
    result = run_engine(data)
    assert result.coverage.status == meta["_expected_status"]
    for key in meta["_expected_shortfall_keys"]:
        assert key in result.coverage.shortfall
    assert result.summary.auto_fallback_triggered == meta["_expected_auto_fallback_triggered"]
