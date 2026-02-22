# Vehicle Selection — Business Rules

> Read this before modifying:
> `engine/candidate_selector.py`, `engine/phase_a.py`, `engine/phase_b.py`,
> `engine/phase_c.py`, `models/vehicle.py`

---

## Vehicle Types

| Type | Description | Cost Nature |
|---|---|---|
| `own` | Company-owned vehicle | Fixed — sunk cost, already paid |
| `subcontractor` | Third-party supplier vehicle | Variable — cost incurred per trip |

Vehicle types (single, bdouble, etc.) are **dynamic**.
Never hardcode vehicle type values in engine logic.
Sub-groups are created at runtime from whatever types appear in the input.

---

## Vehicle Priority — Config Driven

Priority order is never hardcoded. Always read from `config.vehicle_priority`.

| Config Value | Behaviour |
|---|---|
| `own` | Own vehicles sorted first, subcon after within each candidate list |
| `subcontractor` | Subcon vehicles sorted first, own after |
| `both` | Single pool sorted purely by capacity — no ownership separation |

Applied as a **stable sort** on top of the dual sort.
Stable sort preserves the inner pallet/weight sort order within each ownership group.

---

## The loaded_with Rule — Most Important Rule in the Engine

When a vehicle is first selected, it is marked with `loaded_with`:

```
loaded_with = "pallet"   set when vehicle first selected for pallet orders
loaded_with = "weight"   set when vehicle first selected for weight orders
loaded_with = null       vehicle not yet selected
```

**This rule is absolute — no exceptions in any phase:**

```
IF vehicle.loaded_with == "pallet":
    The truck floor is physically occupied by pallets
    remaining_weight may be > 0 but is IRRELEVANT
    The truck cannot accept any more goods of any kind
    → Only offer this vehicle for more pallet demand
      (if remaining_pallet > 0)

IF vehicle.loaded_with == "weight":
    The truck is loaded with weight-based goods
    remaining_pallet may be > 0 but is IRRELEVANT
    → Only offer this vehicle for more weight demand
      (if remaining_weight > 0)
```

**Why:** A truck loaded to its pallet space limit is physically full.
Even if it has not reached its weight limit on paper, you cannot
load more goods because there is no floor space left.
The same applies in reverse for weight-loaded trucks.

**loaded_with never changes after first assignment.**
First loaded dimension wins — always.

---

## Three Processing Phases

### Phase A — Pallet Preference Orders
- Process all orders where `high_dimension_preference = "pallet_space"`
- Typed orders (specific vehicle type) processed first
- Flexible orders (null vehicle type) used as gap fillers after typed orders
- Vehicles selected here get `loaded_with = "pallet"`

### Phase B — Weight Preference Orders
- Process all orders where `high_dimension_preference = "weight_kg"`
- Same structure as Phase A
- vehicle_pool carries forward from Phase A with reduced remaining capacity
- Vehicles with `loaded_with = "pallet"` are completely excluded
- Vehicles selected here get `loaded_with = "weight"`

### Phase C — Leftover Mixing
- Collects all shortfalls from Phase A and Phase B
- Includes unfulfilled flexible orders from both phases
- Tries to resolve shortfalls using remaining capacity
- Priority 1: already selected vehicles (same loaded_with, same type)
- Priority 2: unselected vehicles
- Threshold check applies when `vehicle_priority = "both"`

---

## get_candidates — Sorting Logic (Option A Dual Sort)

Called in every phase. Returns sorted eligible vehicle list.

### Eligibility Filter (applied before sorting)
```
For selected vehicles:
  loaded_with must match the required dimension
  remaining capacity for that dimension must be > 0

For all vehicles:
  vehicle_type must match (unless flexible order — skip type check)
  must have required dimension capacity field defined (not null)
```

### Sort Order

**For pallet dimension:**
```
PRIMARY:   pallet_space DESC    ← cover pallet demand in fewest picks
SECONDARY: weight_kg ASC        ← among equal pallet vehicles,
                                   prefer lower weight
                                   saves high-weight vehicles for Phase B
```

**For weight dimension:**
```
PRIMARY:   weight_kg DESC       ← cover weight demand in fewest picks
SECONDARY: pallet_space ASC     ← among equal weight vehicles,
                                   prefer lower pallet space
                                   saves high-pallet vehicles
```

### Ownership Priority (stable sort applied after dual sort)
```
vehicle_priority = "own":
    STABLE SORT: own first, subcon second
    (preserves dual sort order within each group)

vehicle_priority = "subcontractor":
    STABLE SORT: subcon first, own second

vehicle_priority = "both":
    No ownership re-sort
    Dual sort is the final order
```

### Known Limitation of Option A
Dual sort is a heuristic improvement — not a guarantee.
It performs well when fleet vehicles have varied pallet/weight ratios.
When vehicles scale proportionally (high pallet always = high weight),
the secondary sort has no effect.
Pre-phase vehicle classification (Option B) addresses this — parked for Phase 2.

---

## Flexible Orders — Vehicle Type Rule

Flexible orders have `vehicle_type_required = null`.
They can use any vehicle type but must respect the `loaded_with` rule:

```
Flexible pallet order in Phase C:
  Can use ANY vehicle type ← no type constraint
  BUT vehicle.loaded_with must = "pallet" ← physical rule still applies
  AND vehicle.remaining_pallet > 0

Flexible weight order in Phase C:
  Can use ANY vehicle type
  BUT vehicle.loaded_with must = "weight"
  AND vehicle.remaining_weight > 0
```

The flexibility is about **vehicle type only**.
Physical loading state always applies regardless of order type.

---

## Cross-Type Fallback

Controlled by `config.allow_cross_type_fallback`.

```
allow_cross_type_fallback = false (default):
  Typed order requires "single" but no single vehicle available
  → Report as shortfall immediately
  → Do not try bdouble or other types

allow_cross_type_fallback = true:
  Typed order requires "single" but no single vehicle available
  → Retry with any vehicle type
  → If still no vehicle → report shortfall
```

Applies in Phase A, Phase B, and Phase C equally.

---

## Phase C Threshold (vehicle_priority = "both" only)

When `vehicle_priority = "both"`, own vehicles in Phase C are subject
to a utilisation threshold check.

```
threshold = vehicle.max_[dimension] * (config.phase_c_own_utilisation_threshold / 100)

IF leftover_amount < threshold AND vehicle.ownership_type == "own":
    SKIP this own vehicle
    → subcontractor will handle the small leftover instead

IF leftover_amount >= threshold:
    Use this own vehicle
```

**Option D** — threshold is calculated against the specific candidate
vehicle being evaluated, not fleet average or smallest/largest vehicle.

Applies to:
- Priority 1 (already selected own vehicles)
- Priority 2 (unselected own vehicles)
- Both pallet and weight dimensions

Does NOT apply when `vehicle_priority = "own"` or `"subcontractor"`.

---

## auto_fallback_to_leased

```
auto_fallback_to_leased = false:
  If own fleet cannot cover demand within a phase
  → Report shortfall, do not engage subcontractors

auto_fallback_to_leased = true:
  If own fleet cannot cover demand within a phase
  → Bring in subcontractors to cover remaining gap
  → summary.auto_fallback_triggered = true
```

---

## cost_per_trip

Included in vehicle schema but **unused in Phase 1**.
Reserved for Phase 5 cost-aware subcontractor selection.
Do not add cost logic anywhere in Phase 1 code.

---

## Decisions Log

| Decision | Rationale |
|---|---|
| loaded_with rule — absolute, no exceptions | Physical truck loading reality |
| Own before subcon by default | Sunk cost vs variable cost |
| Config-driven priority | Reusable across different client deployments |
| Option A dual sort | Practical improvement without complexity of Option B |
| Option B parked for Phase 2 | Diminishing returns for Phase 1 scope |
| Flexible orders respect loaded_with | Physical reality applies regardless of order flexibility |
| Option D threshold (per candidate vehicle) | Most accurate utilisation comparison |
| Vehicle types dynamic | Fleet composition varies per client |

---

*Status: Final — Phase 1*
