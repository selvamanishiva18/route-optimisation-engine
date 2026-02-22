# Route Optimisation Engine

A stateless backend fleet selection engine built with FastAPI. Given a batch of delivery orders, a fleet of available vehicles, and configuration rules, the engine determines the **minimum number of vehicles** needed to cover all demand.

## Purpose

In logistics and fleet management, dispatchers need to decide which vehicles to assign for a given set of orders. This engine automates that decision by:

- Matching orders to vehicles based on **capacity dimensions** (pallet space and weight)
- Respecting **vehicle type requirements** (e.g., single, bdouble) and **flexible orders** that can use any type
- Prioritising **own fleet** over subcontractors, with configurable fallback rules
- Processing in three phases — **Phase A** (pallet preference), **Phase B** (weight preference), **Phase C** (leftover mixing) — to minimise the number of vehicles selected
- Enforcing the **loaded_with rule**: once a vehicle is loaded with a pallet or weight order, it is locked to that dimension for the entire batch

## Tech Stack

- **Python 3.11+**
- **FastAPI** — REST API framework
- **Pydantic v2** — request/response validation
- **Uvicorn** — ASGI server
- **Pytest** — test framework (60 tests, 27 fixture-driven scenarios)

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip

### Installation

```bash
git clone https://github.com/selvamanishiva18/route-optimisation-engine.git
cd route-optimisation-engine
pip install -r requirements.txt
```

### Run the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000` and Swagger UI at `http://localhost:8000/docs`.

### Run Tests

```bash
pytest
```

## API Endpoint

```
POST /select-vehicles
Content-Type: application/json
```

## Sample Input

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

## Sample Output

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
        "pallet": 10,
        "weight": 5000
      }
    },
    {
      "vehicle_id": "VEH-002",
      "vehicle_type": "bdouble",
      "ownership_type": "subcontractor",
      "loaded_with": "weight",
      "selected_phase": "B",
      "original_capacity": {
        "max_pallet_space": 200,
        "max_weight_kg": 8000
      },
      "remaining_capacity": {
        "pallet": 200,
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
      "weight_kg": 8000
    },
    "shortfall": null
  },
  "summary": {
    "total_orders": 3,
    "pallet_orders_count": 2,
    "weight_orders_count": 1,
    "flexible_orders_count": 1,
    "vehicle_types_in_batch": ["bdouble", "single"],
    "own_vehicles_selected": 1,
    "subcon_vehicles_selected": 1,
    "total_vehicles_selected": 2,
    "auto_fallback_triggered": true,
    "cross_type_fallback_triggered": false,
    "phase_c_triggered": false
  }
}
```

## Configuration Options

| Field | Default | Description |
|---|---|---|
| `vehicle_priority` | `"own"` | Ownership preference: `"own"`, `"subcontractor"`, or `"both"` |
| `auto_fallback_to_leased` | `false` | Use subcontractors when own fleet is insufficient |
| `own_vehicle_selection` | `"fewest"` | Selection strategy for own vehicles |
| `subcontractor_selection` | `"fewest"` | Selection strategy for subcontractor vehicles |
| `allow_cross_type_fallback` | `false` | Try other vehicle types when required type is unavailable |
| `phase_c_own_utilisation_threshold` | `50` | Min % utilisation for own vehicles in Phase C (when priority=both) |

## Coverage Status

| Status | Meaning |
|---|---|
| `full` | All demand fully covered by selected vehicles |
| `partial` | Some demand remains unmet — shortfall details included |
| `none` | No vehicles were selected |

## Project Structure

```
route-optimisation-engine/
├── main.py                     # FastAPI app — POST /select-vehicles
├── models/
│   ├── order.py                # Order and CapacityRequired models
│   └── vehicle.py              # Vehicle and VehicleCapacity models
├── engine/
│   ├── validator.py            # Input validation and normalisation
│   ├── pool_builder.py         # Build mutable vehicle pool
│   ├── order_grouper.py        # Group orders by type and dimension
│   ├── candidate_selector.py   # Candidate filtering and sorting
│   ├── phase_a.py              # Pallet preference processing
│   ├── phase_b.py              # Weight preference processing
│   ├── phase_c.py              # Leftover mixing and shortfall resolution
│   └── coverage.py             # Coverage status and response assembly
├── schemas/
│   ├── request.py              # EngineRequest schema
│   └── response.py             # EngineResponse schema
├── tests/                      # 60 tests with 27 JSON fixture scenarios
├── docs/                       # Detailed documentation
└── requirements.txt
```

## Author

**selvamanishiva18** — [GitHub](https://github.com/selvamanishiva18)

## License

This project is proprietary. All rights reserved.
