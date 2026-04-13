"""GET /config endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..dependencies import AppState
from ..schemas import ConfigResponse

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
def get_config(request: Request) -> ConfigResponse:
    state: AppState = request.app.state.app_state
    cfg = state.config
    return ConfigResponse(
        setup_fee_rate=cfg.setup_fee_rate,
        premium_tax_rate=cfg.premium_tax_rate,
        normal_tax_rate=cfg.normal_tax_rate,
        is_premium=cfg.is_premium,
        profit_weight=cfg.profit_weight,
        focus_weight=cfg.focus_weight,
        volume_weight=cfg.volume_weight,
        freshness_weight=cfg.freshness_weight,
        min_profit=cfg.min_profit,
        sales_tax_rate=cfg.sales_tax_rate,
    )
