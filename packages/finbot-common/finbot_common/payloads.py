"""TradeOrder / TradeOpened contracts for FinBot v2."""
from __future__ import annotations

import uuid
from typing import Any


REQUIRED_ORDER_FIELDS = (
    "order_id",
    "client_order_id",
    "block_id",
    "strategy",
    "symbol",
    "direction",
    "tier",
    "venue",
    "leverage",
    "entry",
    "quantity",
    "notional_usdt",
    "exit",
    "execution",
)


def _require(obj: dict, key: str, parent: str = "") -> Any:
    if key not in obj:
        raise ValueError(f"Missing field: {parent}{key}")
    return obj[key]


def validate_trade_order(data: dict) -> dict:
    """Validate and normalize a trade.order payload."""
    if not isinstance(data, dict):
        raise ValueError("TradeOrder must be a dict")

    for field in REQUIRED_ORDER_FIELDS:
        _require(data, field)

    direction = str(data["direction"]).upper()
    if direction not in ("LONG", "SHORT"):
        raise ValueError(f"Invalid direction: {direction}")

    venue = str(data["venue"]).lower()
    if venue not in ("spot", "futures"):
        raise ValueError(f"Invalid venue: {venue}")

    entry = data["entry"]
    entry_type = str(entry.get("type", "market")).lower()
    if entry_type not in ("market", "limit"):
        raise ValueError(f"Invalid entry.type: {entry_type}")

    exit_cfg = data["exit"]
    for k in ("sl_price", "tp_price", "max_hold_hours", "mode"):
        if k not in exit_cfg:
            raise ValueError(f"Missing exit.{k}")

    if exit_cfg["mode"] not in ("software", "exchange_oco", "exchange_bracket"):
        raise ValueError(f"Invalid exit.mode: {exit_cfg['mode']}")

    data = dict(data)
    data["direction"] = direction
    data["venue"] = venue
    data["entry"] = {**entry, "type": entry_type}
    return data


def new_order_id() -> str:
    return str(uuid.uuid4())


class TradeOrder:
    """Builder helper for leme-engine."""

    @staticmethod
    def build(
        *,
        block_id: str,
        strategy: str,
        symbol: str,
        direction: str,
        tier: str,
        venue: str,
        leverage: int,
        quantity: float,
        notional_usdt: float,
        sl_price: float,
        tp_price: float,
        client_order_id: str,
        entry_type: str = "market",
        entry_price: float | None = None,
        entry_timeout_sec: int | None = None,
        entry_fallback: str = "abort",
        max_hold_hours: float = 12,
        rsi_exit: float = 70,
        trailing_enabled: bool = False,
        trailing_activation_atr: float = 1.0,
        trailing_distance_atr: float = 2.0,
        exit_mode: str = "software",
        signal: dict | None = None,
        execution: dict | None = None,
        order_id: str | None = None,
    ) -> dict:
        payload = {
            "order_id": order_id or new_order_id(),
            "client_order_id": client_order_id,
            "block_id": block_id,
            "strategy": strategy,
            "symbol": symbol,
            "direction": direction.upper(),
            "tier": tier,
            "venue": venue.lower(),
            "leverage": int(leverage),
            "entry": {
                "type": entry_type,
                "price": entry_price,
                "timeout_sec": entry_timeout_sec,
                "fallback": entry_fallback,
            },
            "quantity": float(quantity),
            "notional_usdt": float(notional_usdt),
            "exit": {
                "sl_price": float(sl_price),
                "tp_price": float(tp_price),
                "max_hold_hours": float(max_hold_hours),
                "rsi_exit": float(rsi_exit),
                "trailing": {
                    "enabled": bool(trailing_enabled),
                    "activation_atr": float(trailing_activation_atr),
                    "distance_atr": float(trailing_distance_atr),
                },
                "mode": exit_mode,
            },
            "execution": execution
            or {
                "max_retries": 3,
                "retry_delay_sec": 1,
                "on_oco_failure": "market_close",
                "dust_tolerance_usdt": 1.0,
            },
            "signal": signal or {},
        }
        return validate_trade_order(payload)


class TradeOpened:
    @staticmethod
    def from_order(
        order: dict,
        *,
        entry_price: float,
        quantity_requested: float,
        quantity_filled: float,
        quantity_exit: float,
        exchange_order_id: str | None = None,
        status: str = "OPEN",
    ) -> dict:
        opened = dict(order)
        opened.update(
            {
                "status": status,
                "entry_price": float(entry_price),
                "quantity_requested": float(quantity_requested),
                "quantity_filled": float(quantity_filled),
                "quantity_exit": float(quantity_exit),
                "exchange_order_id": exchange_order_id,
            }
        )
        return opened
