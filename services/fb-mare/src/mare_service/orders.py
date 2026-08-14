from __future__ import annotations

import uuid

from .strategy import MareSignal


def build_order(signal: MareSignal, notional_usdt: float) -> dict:
    if not signal.accepted or not signal.direction:
        raise ValueError("only accepted signals can become orders")
    price = signal.price
    risk_distance = max(signal.atr * 1.8, price * 0.006)
    reward_distance = max(signal.atr * 2.7, price * 0.009)
    if signal.direction == "LONG":
        sl_price, tp_price = price - risk_distance, price + reward_distance
        venue = "spot"
    else:
        sl_price, tp_price = price + risk_distance, price - reward_distance
        venue = "futures"
    quantity = max(notional_usdt / max(price, 1e-12), 0.0)
    client_id = f"mare-{signal.direction[0]}-{signal.symbol.split('/')[0][:6]}-{uuid.uuid4().hex[:6]}"[:36]
    return {
        "order_id": str(uuid.uuid4()),
        "client_order_id": client_id,
        "block_id": "mare",
        "strategy": "elder_triple_screen",
        "symbol": signal.symbol,
        "direction": signal.direction,
        "tier": "Major",
        "venue": venue,
        "leverage": 1,
        "entry": {"type": "market", "price": None, "timeout_sec": None, "fallback": "abort"},
        "quantity": float(quantity),
        "notional_usdt": float(notional_usdt),
        "exit": {
            "sl_price": float(sl_price),
            "tp_price": float(tp_price),
            "max_hold_hours": 24.0,
            "rsi_exit": 70.0,
            "trailing": {"enabled": True, "activation_atr": 1.0, "distance_atr": 2.0},
            "mode": "software",
        },
        "execution": {"max_retries": 3, "retry_delay_sec": 1, "on_oco_failure": "market_close", "dust_tolerance_usdt": 1.0},
        "signal": signal.as_dict(),
    }
