"""
Order Grouper — Step 3
=======================
Read docs/capacity-constraints.md before modifying.

Responsibilities:
- Split orders into four groups:
    typed_pallet_groups  — { vehicle_type: [orders] }  high_dim=pallet, type!=null
    typed_weight_groups  — { vehicle_type: [orders] }  high_dim=weight, type!=null
    flexible_pallet_orders — [orders]  high_dim=pallet, type=null
    flexible_weight_orders — [orders]  high_dim=weight, type=null

- Vehicle types are dynamic — never hardcoded
- Sub-groups created at runtime from whatever types appear in orders

Processing order in each phase:
  1. Typed sub-groups (specific vehicle type required)
  2. Flexible orders (gap fill in selected vehicles first)
"""

from typing import Dict, List, Any
from models.order import Order


class OrderGroups:
    def __init__(self):
        self.typed_pallet_groups: Dict[str, List[Order]] = {}
        self.typed_weight_groups: Dict[str, List[Order]] = {}
        self.flexible_pallet_orders: List[Order] = []
        self.flexible_weight_orders: List[Order] = []


def group(orders: List[Order]) -> OrderGroups:
    """
    Groups orders by dimension preference and vehicle type.
    Returns OrderGroups with four categorised lists.
    """
    groups = OrderGroups()

    for order in orders:
        pref = order.high_dimension_preference
        vtype = order.vehicle_type_required

        if pref == "pallet_space":
            if vtype is not None:
                groups.typed_pallet_groups.setdefault(vtype, []).append(order)
            else:
                groups.flexible_pallet_orders.append(order)
        elif pref == "weight_kg":
            if vtype is not None:
                groups.typed_weight_groups.setdefault(vtype, []).append(order)
            else:
                groups.flexible_weight_orders.append(order)

    return groups
