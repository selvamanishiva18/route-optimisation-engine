# API Contract

> Read this before modifying: `schemas/request.py`, `schemas/response.py`, `engine/validator.py`

---

## Endpoint

```
POST /select-vehicles
Content-Type: application/json
```

---

## Request Schema

```json
{
  "config": {
    "vehicle_priority": "own",
    "auto_fallback_to_leased": true,
    "own_vehicle_selection": "fewest",
    "subcontractor_selection": "fewest",
    "allow_cross_type_fallback": false,
    "phase_c_own_utilisation_threshold": 50
  },
  "orders": [
    {
      "order_id": "ORD-001",
      "vehicle_type_required": "single",
      "high_dimension_preference": "pallet_space",
      "capacity_required": {
        "pallet_space": 100,
        "weight_kg": null
      }
    },
    {
      "order_id": "ORD-002",
      "vehicle_type_required": "bdouble",
      "high_dimension_preference": "weight_kg",
      "capacity_required": {
        "pallet_space": null,
        "weight_kg": 3000
      }
    },
    {
      "order_id": "ORD-003",
      "vehicle_type_required": null,
      "high_dimension_preference": "pallet_space",
      "capacity_required": {
        "pallet_space": 40,
        "weight_kg": null
      }
    }
  ],
  "vehicles": [
    {
      "vehicle_id": "VEH-001",
      "vehicle_type": "single",
      "type": "own",
      "available": true,
      "cost_per_trip": null,
      "capacity": {
        "max_pallet_space": 150,
        "max_weight_kg": 5000
      }
    },
    {
      "vehicle_id": "VEH-002",
      "vehicle_type": "bdouble",
      "type": "subcontractor",
      "available": true,
      "cost_per_trip": 250.00,
      "capacity": {
        "max_pallet_space": 200,
        "max_weight_kg": 8000
      }
    }
  ]
}
```

---

## Config Fields

| Field | Type | Default | Options | Purpose |
|---|---|---|---|---|
| `vehicle_priority` | string | `"own"` | `"own"` `"subcontractor"` `"both"` | Ownership preference in candidate selection |
| `auto_fallback_to_leased` | bool | `false` | `true` `false` | Use subcon when own fleet insufficient |
| `own_vehicle_selection` | string | `"fewest"` | `"fewest"` | Phase 1 only — strategy for own vehicle selection |
| `subcontractor_selection` | string | `"fewest"` | `"fewest"` | Phase 1 only — strategy for subcon selection |
| `allow_cross_type_fallback` | bool | `false` | `true` `false` | Try other vehicle types when required type unavailable |
| `phase_c_own_utilisation_threshold` | int | `50` | 0–100 | Min % utilisation for own vehicle in Phase C when priority=both |

---

## Order Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `order_id` | string | Yes | Must be unique in batch |
| `vehicle_type_required` | string or null | No | `null` = flexible, any vehicle type |
| `high_dimension_preference` | string or null | Conditional | Auto-set if only one dimension non-null. Mandatory if both non-null. Values: `"pallet_space"` or `"weight_kg"` |
| `capacity_required.pallet_space` | int or null | Conditional | At least one dim must be non-null. 0 treated as null. |
| `capacity_required.weight_kg` | float or null | Conditional | At least one dim must be non-null. 0 treated as null. |

---

## Vehicle Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `vehicle_id` | string | Yes | Must be unique in batch |
| `vehicle_type` | string | Yes | Dynamic — any value e.g. "single", "bdouble", "semi" |
| `type` | string | Yes | `"own"` or `"subcontractor"` |
| `available` | bool | Yes | `false` = excluded from all selection |
| `cost_per_trip` | float or null | No | Reserved — unused in Phase 1 |
| `capacity.max_pallet_space` | int or null | No | `null` = vehicle cannot serve pallet orders |
| `capacity.max_weight_kg` | float or null | No | `null` = vehicle cannot serve weight orders |

---

## Response Schema

```json
{
  "selected_vehicles": [
    {
      "vehicle_id": "VEH-001",
      "vehicle_type": "single",
      "ownership_type": "own",
      "loaded_with": "pallet",
      "selected_phase": "A",
      "original_capacity": {
        "max_pallet_space": 150,
        "max_weight_kg": 5000
      },
      "remaining_capacity": {
        "pallet": 50,
        "weight": 5000
      }
    }
  ],
  "coverage": {
    "status": "full",
    "total_demand": {
      "pallet_space": 140,
      "weight_kg": 3000
    },
    "total_capacity_selected": {
      "pallet_space": 150,
      "max_weight_kg": 5000
    },
    "shortfall": null
  },
  "summary": {
    "total_orders": 3,
    "pallet_orders_count": 2,
    "weight_orders_count": 1,
    "flexible_orders_count": 1,
    "vehicle_types_in_batch": ["single", "bdouble"],
    "own_vehicles_selected": 1,
    "subcon_vehicles_selected": 0,
    "total_vehicles_selected": 1,
    "auto_fallback_triggered": false,
    "cross_type_fallback_triggered": false,
    "phase_c_triggered": false
  }
}
```

---

## Response Field Details

### selected_vehicles

| Field | Type | Notes |
|---|---|---|
| `vehicle_id` | string | |
| `vehicle_type` | string | "single", "bdouble", etc. |
| `ownership_type` | string | "own" or "subcontractor" |
| `loaded_with` | string | "pallet" or "weight" — first dimension loaded |
| `selected_phase` | string | "A", "B", or "C" |
| `original_capacity` | object | max values — unchanged |
| `remaining_capacity` | object | after all deductions |

### coverage.status Values

| Value | Meaning |
|---|---|
| `full` | All demand dimensions fully covered |
| `partial` | At least one sub-group has unmet demand |
| `none` | No vehicles selected |

### coverage.shortfall

Only present when `status = "partial"`.
Format: `{ "{vehicle_type}_{dimension}": amount }`

```json
"shortfall": {
  "single_weight": 1000,
  "bdouble_pallet": 20,
  "flexible_weight": 800
}
```

Only dimensions with shortfall > 0 are included.

### summary flags

| Field | When true |
|---|---|
| `auto_fallback_triggered` | Subcon used because own fleet was insufficient |
| `cross_type_fallback_triggered` | Different vehicle type used due to type unavailability |
| `phase_c_triggered` | Phase C ran (shortfalls existed from Phase A or B) |

---

## Validation Errors

```json
{
  "detail": "Validation error message"
}
```

| HTTP Code | Scenario |
|---|---|
| 422 | Pydantic schema validation failed |
| 400 | Business rule validation failed |
| 500 | Unexpected engine error |

---

## Reserved Fields (Do Not Use in Phase 1)

| Field | Reserved For |
|---|---|
| `cost_per_trip` | Phase 5 — cost-aware subcontractor selection |
| `own_vehicle_selection: "tightest_fit"` | Phase 2 — advanced selection strategies |
| `own_vehicle_selection: "balanced_load"` | Phase 2 |
| `volume_m3` | Future phase — volume dimension |

---

*Status: Final — Phase 1*
