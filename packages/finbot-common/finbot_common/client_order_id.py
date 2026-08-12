"""Binance newClientOrderId builder (max 36 chars)."""
from __future__ import annotations

import secrets

TIER_CODES = {
    "Major": "Maj",
    "Strong Alt": "Alt",
    "High Volatility": "HV",
}


def build_client_order_id(
    block_id: str,
    direction: str,
    tier: str,
    symbol: str,
    seq: str | None = None,
) -> str:
    base = symbol.split("/")[0][:6]
    tier_code = TIER_CODES.get(tier, tier[:3])
    dir_code = "L" if direction.upper() == "LONG" else "S"
    suffix = seq or secrets.token_hex(2)
    cid = f"{block_id}-{dir_code}-{tier_code}-{base}-{suffix}"
    return cid[:36]
