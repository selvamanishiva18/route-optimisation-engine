"""
Route Optimisation Engine — Phase 1
====================================
Entry point. Wiring only — no business logic here.
All logic lives in engine/

Read CLAUDE.md before modifying this file.
"""

from fastapi import FastAPI, HTTPException
from schemas.request import EngineRequest
from schemas.response import EngineResponse
from engine import validator, pool_builder, order_grouper, phase_a, phase_b, phase_c, coverage

app = FastAPI(
    title="Route Optimisation Engine",
    description="Fleet selection engine — Phase 1",
    version="1.0.0"
)


@app.post("/select-vehicles", response_model=EngineResponse)
def select_vehicles(request: EngineRequest) -> EngineResponse:
    """
    Accepts orders + vehicles + config.
    Returns selected vehicles that collectively cover all order demand.
    """
    try:
        request = validator.validate(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    vehicle_pool = pool_builder.build(request.vehicles)
    order_groups = order_grouper.group(request.orders)

    a_shortfalls, a_flex_unfulfilled, a_auto_fb, a_cross_fb = phase_a.run(
        vehicle_pool, order_groups, request.config
    )

    b_shortfalls, b_flex_unfulfilled, b_auto_fb, b_cross_fb = phase_b.run(
        vehicle_pool, order_groups, request.config
    )

    c_shortfalls, c_triggered = phase_c.run(
        vehicle_pool,
        a_shortfalls, b_shortfalls,
        a_flex_unfulfilled, b_flex_unfulfilled,
        request.config,
    )

    return coverage.build_response(
        vehicle_pool=vehicle_pool,
        orders=request.orders,
        phase_C_shortfalls=c_shortfalls,
        phase_C_triggered=c_triggered,
        auto_fallback_triggered=a_auto_fb or b_auto_fb,
        cross_type_fallback_triggered=a_cross_fb or b_cross_fb,
        config=request.config,
    )
