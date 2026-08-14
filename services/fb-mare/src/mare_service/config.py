from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    nats_url: str = os.getenv("NATS_URL", "nats://crypto-nats:4222")
    database_url: str = os.getenv("DATABASE_URL", "")
    universe_subject: str = os.getenv("MARE_UNIVERSE_SUBJECT", "leme.universe")
    live_orders_enabled: bool = _bool("MARE_LIVE_ORDERS_ENABLED", False)
    notional_usdt: float = float(os.getenv("MARE_NOTIONAL_USDT", "10"))
    min_score: float = float(os.getenv("MARE_MIN_SCORE", "0.65"))
    tide_timeframe: str = os.getenv("MARE_TIDE_TIMEFRAME", "4h")
    wave_timeframe: str = os.getenv("MARE_WAVE_TIMEFRAME", "1h")
    ripple_timeframe: str = os.getenv("MARE_RIPPLE_TIMEFRAME", "15m")
    max_tide_candles: int = int(os.getenv("MARE_TIDE_CANDLES", "180"))
    max_wave_candles: int = int(os.getenv("MARE_WAVE_CANDLES", "240"))
    max_ripple_candles: int = int(os.getenv("MARE_RIPPLE_CANDLES", "240"))
    max_assets_per_cycle: int = int(os.getenv("MARE_MAX_ASSETS", "20"))
    cycle_timeout_sec: int = int(os.getenv("MARE_CYCLE_TIMEOUT_SEC", "300"))
