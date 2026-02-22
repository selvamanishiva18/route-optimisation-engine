# CLAUDE.md — Route Optimisation Engine

## What This Project Is
A stateless backend fleet selection engine.
Single endpoint: `POST /select-vehicles`
Input: orders + vehicles + config → Output: minimum vehicles needed to cover demand.

Phase 1: capacity matching only.
  - No routing
  - No order-to-vehicle assignment
  - No distance or ETA calculation

---

## How To Run
```bash
pip install -r requirements.txt
uvicorn main:app --reload
# Swagger UI: http://localhost:8000/docs
```

---

## Project Structure
```
route-optimisation-engine/
├── main.py                        # FastAPI app — POST /select-vehicles
├── models/
│   ├── order.py                   # Order, CapacityRequired
│   └── vehicle.py                 # Vehicle, VehicleCapacity, VehicleType
├── engine/
│   ├── validator.py               # Step 1 — input validation
│   ├── pool_builder.py            # Step 2 — build mutable vehicle pool
│   ├── order_grouper.py           # Step 3 — group orders by type + dimension
│   ├── candidate_selector.py      # Step 4 — get_candidates() helper
│   ├── phase_a.py                 # Step 5 — pallet preference orders
│   ├── phase_b.py                 # Step 6 — weight preference orders
│   ├── phase_c.py                 # Step 7 — leftover mixing
│   └── coverage.py                # Step 8 — coverage status + output
├── schemas/
│   ├── request.py                 # EngineRequest schema
│   └── response.py                # EngineResponse schema
├── tests/
│   ├── test_validator.py
│   ├── test_pool_builder.py
│   ├── test_order_grouper.py
│   ├── test_candidate_selector.py
│   ├── test_phase_a.py
│   ├── test_phase_b.py
│   ├── test_phase_c.py
│   ├── test_coverage.py
│   └── fixtures/                  # JSON test input/output pairs
└── docs/
    ├── vehicle-selection.md       # Vehicle priority, sorting, phase rules, loaded_with
    ├── capacity-constraints.md    # Dimension rules, aggregation, order grouping
    ├── api-contract.md            # Full input/output JSON contract + config fields
    └── testing-guide.md           # Fixture conventions, test scenarios, patterns
```

---

## ⚠️ Before Modifying Any File — Read This First

| File(s) | Read Before Changing |
|---|---|
| `engine/candidate_selector.py` | `docs/vehicle-selection.md` |
| `engine/phase_a.py` | `docs/vehicle-selection.md` + `docs/capacity-constraints.md` |
| `engine/phase_b.py` | `docs/vehicle-selection.md` + `docs/capacity-constraints.md` |
| `engine/phase_c.py` | `docs/vehicle-selection.md` + `docs/capacity-constraints.md` |
| `engine/pool_builder.py` | `docs/capacity-constraints.md` |
| `engine/order_grouper.py` | `docs/capacity-constraints.md` |
| `engine/validator.py` | `docs/capacity-constraints.md` + `docs/api-contract.md` |
| `engine/coverage.py` | `docs/capacity-constraints.md` |
| `models/order.py` | `docs/capacity-constraints.md` |
| `models/vehicle.py` | `docs/vehicle-selection.md` |
| `schemas/request.py` | `docs/api-contract.md` |
| `schemas/response.py` | `docs/api-contract.md` |
| `tests/` | `docs/testing-guide.md` |

After modifying business logic in code, check if the corresponding doc needs updating.
**Code and docs must stay in sync.**

---

## Key Conventions
- All business logic lives in `engine/` — not in `main.py` or schemas
- `main.py` is wiring only — no logic
- Pydantic v2 for all models and schemas
- Every engine module has a corresponding test file
- Fixtures are JSON files — one scenario per file, named descriptively
- `loaded_with` rule enforced in every phase — no exceptions ever
- Vehicle types are dynamic — never hardcoded in engine logic
- Stable sort must be used when applying ownership priority on top of dual sort

---

## Phase Roadmap
| Phase | Scope | Status |
|---|---|---|
| 1 | Fleet selection — which vehicles are needed | 🔲 Current |
| 2 | Pre-phase vehicle classification (Option B scoring) | 🔲 |
| 3 | Order-to-vehicle assignment | 🔲 |
| 4 | OSM/Valhalla routing integration per vehicle | 🔲 |
| 5 | Cost-aware subcontractor selection (cost_per_trip) | 🔲 |
| 6 | Multi-stop TSP/VRP optimisation | 🔲 |
| 7 | Time windows, SLA tiers, OR-Tools | 🔲 |

---

## Decisions Log
| Date | Decision | Rationale |
|---|---|---|
| 2026-02-22 | Phase 1 = fleet selection only | Validate core logic first |
| 2026-02-22 | Dimensions: pallet_space + weight_kg only | volume_m3 parked for later |
| 2026-02-22 | loaded_with rule — strict, no exceptions | Physical truck loading reality |
| 2026-02-22 | Three phases: A=pallet, B=weight, C=mixing | Process by dimension preference |
| 2026-02-22 | Option A dual sort | Save high-weight vehicles for Phase B |
| 2026-02-22 | Vehicle types dynamic | Fleet varies per client |
| 2026-02-22 | Option B pre-phase classification parked | Phase 2 enhancement |
| 2026-02-22 | Config-driven priority and fallback | Reusable across clients |
| 2026-02-22 | Flexible orders use loaded_with rule same as typed | Physical reality applies to all |
| 2026-02-22 | Phase C threshold applies per candidate vehicle (Option D) | Most accurate comparison |

---

*Status: Phase 1 — Ready for Implementation*
