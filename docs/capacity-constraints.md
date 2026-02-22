# Capacity Constraints — Business Rules

> Read this before modifying:
> `engine/validator.py`, `engine/pool_builder.py`, `engine/order_grouper.py`,
> `engine/phase_a.py`, `engine/phase_b.py`, `engine/phase_c.py`,
> `engine/coverage.py`, `models/order.py`

---

## Capacity Dimensions — Phase 1

Two active dimensions in Phase 1:

| Dimension | Unit | Order Field | Vehicle Field |
|---|---|---|---|
| Pallet Space | count / units | `pallet_space` | `max_pallet_space` |
| Weight | kilograms | `weight_kg` | `max_weight_kg` |

**volume_m3 is parked — not implemented in Phase 1.**

---

## Null vs Zero — Critical Distinction

```
null  = this dimension is NOT applicable to this order/vehicle
        → excluded from all checks and aggregation

0     = treated same as null
        → validator converts 0 to null at input time
        → a zero-capacity order or vehicle makes no sense

negative = validation error — rejected immediately
```

**At least one dimension must be non-null per order.**
An order with both `pallet_space = null` and `weight_kg = null` is rejected.

---

## high_dimension_preference — Order Level

Every order must declare which dimension is its primary concern.
This drives which phase the order is processed in.

```
high_dimension_preference = "pallet_space"
    → order goes into Phase A (pallet processing)
    → pallet_space must be non-null

high_dimension_preference = "weight_kg"
    → order goes into Phase B (weight processing)
    → weight_kg must be non-null
```

**Auto-set rules (applied in validator):**
```
IF pallet_space is not null AND weight_kg is null:
    SET high_dimension_preference = "pallet_space"  ← auto

IF weight_kg is not null AND pallet_space is null:
    SET high_dimension_preference = "weight_kg"  ← auto

IF both pallet_space and weight_kg are not null:
    high_dimension_preference is MANDATORY
    → validation error if missing
    Engine cannot assume which dimension is primary
    when both are present
```

---

## vehicle_type_required — Order Level

```
"single"   → order must be served by a single vehicle type
"bdouble"  → order must be served by a bdouble vehicle type
null       → flexible — order can go into any vehicle type
```

Vehicle types are dynamic — values come from the input, never hardcoded.

**Flexible orders (null):**
- Processed after typed orders in each phase
- Used as gap fillers in already-selected vehicles first
- Can use any vehicle type
- Must still respect `loaded_with` rule (see vehicle-selection.md)

---

## Order Grouping Logic

Orders are grouped in Step 3 before any phase runs:

```
typed_pallet_groups  = { "single": [...], "bdouble": [...], ... }
typed_weight_groups  = { "single": [...], "bdouble": [...], ... }
flexible_pallet_orders = [...]   # high_dimension_preference=pallet, type=null
flexible_weight_orders = [...]   # high_dimension_preference=weight, type=null
```

Processing order within each phase:
1. Typed sub-groups (specific vehicle type required)
2. Flexible orders (gap fill in selected vehicles first, then unselected)

---

## Demand Aggregation

Aggregated per phase and per vehicle type sub-group:

```
FOR typed_pallet_groups["single"]:
    demand = SUM of pallet_space from all single-type pallet orders

FOR typed_weight_groups["bdouble"]:
    demand = SUM of weight_kg from all bdouble-type weight orders

FOR flexible_pallet_orders:
    demand = SUM of pallet_space from all flexible pallet orders

FOR flexible_weight_orders:
    demand = SUM of weight_kg from all flexible weight orders
```

Also aggregated globally for output summary:
```
total_pallet_demand = SUM of pallet_space from ALL orders where not null
total_weight_demand = SUM of weight_kg from ALL orders where not null
```

---

## Vehicle Pool — Mutable State

Each vehicle in the pool has two sets of values:

```
Original (never changes):
  max_pallet_space   ← used for threshold calculations in Phase C
  max_weight_kg      ← used for threshold calculations in Phase C

Remaining (mutable — reduced as vehicles are selected):
  remaining_pallet   ← starts = max_pallet_space
  remaining_weight   ← starts = max_weight_kg
```

**Deduction formula:**
```
deduct = MIN(vehicle.remaining_[dim], remaining_demand)
remaining_demand -= deduct
vehicle.remaining_[dim] -= deduct
```

MIN prevents:
- Taking more from a vehicle than it has (remaining goes negative)
- Marking demand as met when vehicle was not enough

**Vehicle pool is shared across all phases.**
Capacity deducted in Phase A is not restored for Phase B.
Phase B works with whatever remaining capacity Phase A left.

---

## loaded_with — Physical Loading State

Set on first selection. Never changed after.

```
vehicle.loaded_with = "pallet"  → floor occupied by pallets
vehicle.loaded_with = "weight"  → loaded with weight-based goods
vehicle.loaded_with = null      → not yet selected, fully available
```

Full rule details in `docs/vehicle-selection.md`.

---

## Vehicle Eligibility Per Dimension

A vehicle must have the dimension field defined to serve orders in that dimension:

```
IF order requires pallet_space:
    vehicle.max_pallet_space must NOT be null

IF order requires weight_kg:
    vehicle.max_weight_kg must NOT be null
```

A vehicle missing a required dimension field is excluded for that phase.
It may still be eligible in the other phase if it has that dimension.

Example:
```
VEH-001: max_pallet_space=150, max_weight_kg=null
  → eligible for Phase A (pallet)
  → excluded from Phase B (no weight capacity)

VEH-002: max_pallet_space=null, max_weight_kg=5000
  → excluded from Phase A (no pallet capacity)
  → eligible for Phase B (weight)
```

---

## Coverage Calculation

After all phases complete:

```
remaining per dimension = what was not covered by selected vehicles

IF all dimensions fully covered (remaining = 0):
    status = "full"
    shortfall = null

IF any dimension has remaining > 0:
    status = "partial"
    shortfall = {
        "single_pallet": 20,    ← typed shortfall
        "bdouble_weight": 1000, ← typed shortfall
        "flexible_weight": 800  ← flexible shortfall
    }
    Only include dimensions where shortfall > 0

IF no vehicles were selected at all:
    status = "none"
```

Shortfall key format: `"{vehicle_type}_{dimension}"` for typed orders.
`"flexible_{dimension}"` for flexible orders.

---

## Validation Rules Summary

| Rule | Error |
|---|---|
| orders list empty | "No orders provided" |
| vehicles list empty | "No vehicles provided" |
| all dimensions null in order | "ORD-xxx has no capacity defined" |
| negative dimension value | "ORD-xxx has negative capacity value" |
| both dims present, no preference | "ORD-xxx high_dimension_preference mandatory" |
| preference vs null mismatch | "ORD-xxx prefers pallet_space but value is null" |
| duplicate order_id | "Duplicate order ID ORD-xxx" |
| duplicate vehicle_id | "Duplicate vehicle ID VEH-xxx" |
| all vehicles unavailable | "No available vehicles" |

---

## Decisions Log

| Decision | Rationale |
|---|---|
| volume_m3 parked | Simplify Phase 1 scope |
| 0 treated same as null | Zero capacity order/vehicle makes no sense |
| auto-set preference for single-dim orders | Reduce caller burden for simple orders |
| mandatory preference for dual-dim orders | Engine cannot assume primary dimension |
| Shared mutable vehicle pool across phases | Phase B naturally works with Phase A leftovers |
| MIN deduction formula | Prevents negative remaining, prevents false coverage |
| Shortfall key format: type_dimension | Clear identification of which sub-group failed |

---

*Status: Final — Phase 1*
