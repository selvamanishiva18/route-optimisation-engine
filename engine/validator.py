"""
Validator — Step 1
===================
Read docs/capacity-constraints.md + docs/api-contract.md before modifying.

Responsibilities:
- Reject empty orders or vehicles list
- Reject orders with no capacity dimensions defined
- Reject negative capacity values
- Convert 0 values to null (0 treated same as null)
- Auto-set high_dimension_preference for single-dimension orders
- Enforce mandatory high_dimension_preference when both dims are present
- Validate preference matches available dimension
- Detect duplicate order_id and vehicle_id
- Raise ValueError with clear message for any violation
"""

from schemas.request import EngineRequest


def validate(request: EngineRequest) -> EngineRequest:
    """
    Validates and normalises the engine request.
    Returns the normalised request (with auto-set preferences).
    Raises ValueError with descriptive message on any violation.
    """
    if not request.orders:
        raise ValueError("No orders provided")

    if not request.vehicles:
        raise ValueError("No vehicles provided")

    # Check for duplicate order IDs
    seen_order_ids = set()
    for order in request.orders:
        if order.order_id in seen_order_ids:
            raise ValueError(f"Duplicate order ID {order.order_id}")
        seen_order_ids.add(order.order_id)

    # Check for duplicate vehicle IDs
    seen_vehicle_ids = set()
    for vehicle in request.vehicles:
        if vehicle.vehicle_id in seen_vehicle_ids:
            raise ValueError(f"Duplicate vehicle ID {vehicle.vehicle_id}")
        seen_vehicle_ids.add(vehicle.vehicle_id)

    # Validate and normalise each order
    for order in request.orders:
        cap = order.capacity_required

        # Reject negative values
        if cap.pallet_space is not None and cap.pallet_space < 0:
            raise ValueError(f"{order.order_id} has negative capacity value")
        if cap.weight_kg is not None and cap.weight_kg < 0:
            raise ValueError(f"{order.order_id} has negative capacity value")

        # Convert 0 to null
        if cap.pallet_space is not None and cap.pallet_space == 0:
            cap.pallet_space = None
        if cap.weight_kg is not None and cap.weight_kg == 0:
            cap.weight_kg = None

        # At least one dimension must be non-null
        if cap.pallet_space is None and cap.weight_kg is None:
            raise ValueError(f"{order.order_id} has no capacity defined")

        has_pallet = cap.pallet_space is not None
        has_weight = cap.weight_kg is not None

        # Validate explicit preference matches available dimension (before auto-set)
        if order.high_dimension_preference == "pallet_space" and not has_pallet:
            raise ValueError(
                f"{order.order_id} prefers pallet_space but value is null"
            )
        if order.high_dimension_preference == "weight_kg" and not has_weight:
            raise ValueError(
                f"{order.order_id} prefers weight_kg but value is null"
            )

        # Auto-set or validate high_dimension_preference
        if has_pallet and not has_weight:
            order.high_dimension_preference = "pallet_space"
        elif has_weight and not has_pallet:
            order.high_dimension_preference = "weight_kg"
        elif has_pallet and has_weight:
            if order.high_dimension_preference is None:
                raise ValueError(
                    f"{order.order_id} high_dimension_preference mandatory"
                )

    return request
