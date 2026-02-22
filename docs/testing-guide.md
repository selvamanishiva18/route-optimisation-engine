# Testing Guide

> Read this before modifying anything in `tests/`

---

## Test Philosophy

Each engine module has a dedicated test file.
Tests load JSON fixtures — no logic hardcoded in test functions.
Each fixture represents one named scenario.
Test function names describe the expected outcome clearly.

---

## Structure

```
tests/
├── test_validator.py
├── test_pool_builder.py
├── test_order_grouper.py
├── test_candidate_selector.py
├── test_phase_a.py
├── test_phase_b.py
├── test_phase_c.py
├── test_coverage.py
└── fixtures/
    ├── phase_a/
    │   ├── single_typed_own_covers_fully.json
    │   ├── single_typed_subcon_fallback.json
    │   ├── bdouble_typed_partial_shortfall.json
    │   ├── flexible_fits_gap_in_selected.json
    │   ├── flexible_needs_new_vehicle.json
    │   └── cross_type_fallback_triggered.json
    ├── phase_b/
    │   ├── weight_own_covers_fully.json
    │   ├── weight_pallet_locked_vehicles_excluded.json
    │   ├── weight_subcon_fallback.json
    │   ├── flexible_weight_gap_fill.json
    │   └── weight_shortfall_no_fallback.json
    ├── phase_c/
    │   ├── typed_pallet_resolved_by_selected_vehicle.json
    │   ├── typed_weight_resolved_by_new_vehicle.json
    │   ├── flexible_pallet_any_type_used.json
    │   ├── flexible_weight_loaded_with_respected.json
    │   ├── threshold_own_skipped_subcon_used.json
    │   ├── threshold_own_above_threshold_used.json
    │   └── all_shortfalls_unresolvable.json
    ├── end_to_end/
    │   ├── full_coverage_own_only.json
    │   ├── full_coverage_mixed_fleet.json
    │   ├── partial_coverage_weight_shortage.json
    │   ├── all_vehicles_unavailable.json
    │   ├── no_orders.json
    │   ├── dual_dimension_orders.json
    │   ├── vehicle_priority_both.json
    │   ├── cross_type_fallback_end_to_end.json
    │   └── large_batch_stress.json
```

---

## Fixture Format

```json
{
  "_scenario": "Human readable description of what this tests",
  "_expected_status": "full",
  "_expected_own_selected": 2,
  "_expected_subcon_selected": 0,
  "_expected_phase_c_triggered": false,
  "_expected_shortfall_keys": [],
  "config": { ... },
  "orders": [ ... ],
  "vehicles": [ ... ]
}
```

Fields prefixed with `_` are test metadata.
Strip all `_` fields before passing to engine.
Test functions assert against `_expected_*` values.

---

## Critical Scenarios to Cover

### loaded_with Rule
```
Scenario: Vehicle loaded with pallets in Phase A
          Phase B attempts to use it for weight orders
Expected: Vehicle excluded from Phase B candidates
Fixture:  phase_b/weight_pallet_locked_vehicles_excluded.json
```

### Flexible Gap Fill vs New Vehicle
```
Scenario: Flexible pallet order
          Selected vehicle has remaining_pallet > 0
Expected: Flexible order uses gap — no new vehicle selected
Fixture:  phase_a/flexible_fits_gap_in_selected.json

Scenario: Flexible pallet order
          No selected vehicle has remaining_pallet > 0
Expected: New vehicle selected for flexible order
Fixture:  phase_a/flexible_needs_new_vehicle.json
```

### Phase C Threshold
```
Scenario: vehicle_priority="both"
          leftover_pallet=20, own vehicle max_pallet=150
          threshold=50% → threshold=75
          20 < 75 → skip own vehicle, use subcon
Expected: Subcon selected in Phase C, not own vehicle
Fixture:  phase_c/threshold_own_skipped_subcon_used.json

Scenario: leftover_pallet=100, own vehicle max_pallet=150
          threshold=50% → 75
          100 >= 75 → use own vehicle
Expected: Own vehicle selected in Phase C
Fixture:  phase_c/threshold_own_above_threshold_used.json
```

### Flexible Weight Respects loaded_with
```
Scenario: Phase C flexible weight shortfall
          Vehicle A: loaded_with="pallet", remaining_pallet=0, remaining_weight=5000
          Vehicle B: loaded_with="weight", remaining_weight=2000
Expected: Vehicle A excluded (pallet locked, weight irrelevant)
          Vehicle B used for flexible weight
Fixture:  phase_c/flexible_weight_loaded_with_respected.json
```

### Dual Dimension Orders
```
Scenario: Order has both pallet_space and weight_kg non-null
          high_dimension_preference="pallet_space" mandatory
Expected: Order goes into Phase A pallet group
          Both dimensions present in order but only pallet drives phase
Fixture:  end_to_end/dual_dimension_orders.json
```

### Cross-Type Fallback
```
Scenario: Order requires "single" vehicle type
          No single vehicles available
          allow_cross_type_fallback=true
Expected: Bdouble vehicle used instead
          cross_type_fallback_triggered=true in summary
Fixture:  phase_a/cross_type_fallback_triggered.json

Scenario: Same but allow_cross_type_fallback=false
Expected: Order goes to shortfall immediately
          No cross-type attempt made
```

### Exact Capacity Match
```
Scenario: Vehicle remaining_pallet = 100
          Order pallet_space = 100
Expected: Vehicle selected, remaining_pallet = 0
          Coverage = full (>= not > check)
```

---

## Fixture Scenarios — Phase 1 Coverage

| # | Fixture | Phase | Expected Status |
|---|---|---|---|
| 1 | full_coverage_own_only | E2E | full |
| 2 | full_coverage_mixed_fleet | E2E | full |
| 3 | partial_coverage_weight_shortage | E2E | partial |
| 4 | all_vehicles_unavailable | E2E | none |
| 5 | no_orders | E2E | error |
| 6 | dual_dimension_orders | E2E | full |
| 7 | vehicle_priority_both | E2E | full |
| 8 | cross_type_fallback_end_to_end | E2E | full |
| 9 | large_batch_stress | E2E | full |
| 10 | weight_pallet_locked_vehicles_excluded | Phase B | partial→resolved |
| 11 | flexible_fits_gap_in_selected | Phase A | full |
| 12 | threshold_own_skipped_subcon_used | Phase C | full |
| 13 | flexible_weight_loaded_with_respected | Phase C | full |

---

## How To Run Tests

```bash
pytest tests/ -v
pytest tests/test_phase_a.py -v               # single module
pytest tests/ -k "loaded_with" -v             # filter by name
pytest tests/ -k "phase_c" -v                 # all Phase C tests
```

---

## Adding a New Test Scenario

1. Create JSON fixture in appropriate subfolder under `tests/fixtures/`
2. Name the file descriptively — the name is the scenario
3. Add `_scenario`, `_expected_status`, and relevant `_expected_*` metadata
4. Add test function in corresponding test file:

```python
def test_flexible_weight_respects_loaded_with():
    fixture = load_fixture("phase_c/flexible_weight_loaded_with_respected.json")
    result = run_engine(fixture)
    assert result.coverage.status == fixture["_expected_status"]
    assert result.summary.phase_c_triggered == True
    assert "flexible_weight" not in result.coverage.shortfall
```

5. Run tests to confirm passing

---

## Conventions

- One scenario per fixture file
- Fixture names use snake_case, describe the scenario not the code path
- Never hardcode order IDs or vehicle IDs in assertions — use counts and status
- Test the output contract — not internal module state
- Each fixture must be self-contained — include full config, orders, vehicles
- Large batch fixtures (stress tests) should have at least 20 orders and 5 vehicles

---

*Status: Final — Phase 1*
