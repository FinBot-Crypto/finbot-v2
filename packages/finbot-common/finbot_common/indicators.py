from __future__ import annotations

import numpy as np
import pandas as pd


def compute_atr(highs, lows, closes, period: int = 14) -> float:
    tr = np.maximum.reduce(
        [
            np.array(highs[1:]) - np.array(lows[1:]),
            np.abs(np.array(highs[1:]) - np.array(closes[:-1])),
            np.abs(np.array(lows[1:]) - np.array(closes[:-1])),
        ]
    )
    atr = pd.Series(tr).rolling(period).mean().values
    return float(atr[-1])


def compute_rsi_smooth(closes, period: int = 56) -> tuple[float | None, float | None]:
    if len(closes) < period + 1:
        return None, None
    delta = np.diff(closes)
    gain = np.maximum(delta, 0)
    loss = -np.minimum(delta, 0)
    avg_gain = pd.Series(gain).rolling(period).mean().values
    avg_loss = pd.Series(loss).rolling(period).mean().values
    rsi_14 = 100 - 100 / (1 + avg_gain / (avg_loss + 1e-10))
    rsi_smooth = pd.Series(rsi_14).ewm(span=2, adjust=False).mean().values
    return float(rsi_smooth[-1]), float(rsi_14[-1])


def compute_rsi(closes, period: int = 14) -> float:
    delta = np.diff(closes)
    gain = np.maximum(delta, 0)
    loss = -np.minimum(delta, 0)
    avg_gain = pd.Series(gain).rolling(period).mean().values
    avg_loss = pd.Series(loss).rolling(period).mean().values
    rsi = 100 - 100 / (1 + avg_gain / (avg_loss + 1e-10))
    return float(rsi[-1])
