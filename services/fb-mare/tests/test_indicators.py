import numpy as np
import pandas as pd

from mare_service.indicators import atr, ema, ohlcv_frame, rsi


def frame(values):
    return ohlcv_frame([[i, v, v + 1, v - 1, v, 100] for i, v in enumerate(values)])


def test_ema_and_rsi_are_finite_after_warmup():
    result = frame(np.linspace(100, 120, 80))
    assert np.isfinite(ema(result["close"], 20).iloc[-1])
    assert np.isfinite(rsi(result["close"], 14).iloc[-1])


def test_atr_is_positive():
    result = frame(np.linspace(100, 120, 80))
    assert atr(result, 14).iloc[-1] > 0
