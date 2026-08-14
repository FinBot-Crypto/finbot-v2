import numpy as np

from mare_service.indicators import ohlcv_frame
from mare_service.strategy import evaluate


def make_frame(start, drift, size=180):
    values = start + np.arange(size) * drift + np.sin(np.arange(size) / 3) * 0.3
    return ohlcv_frame([[i, v, v + 0.2, v - 0.2, v, 1000] for i, v in enumerate(values)])


def test_insufficient_data_is_rejected():
    small = make_frame(100, 0.1, 30)
    signal = evaluate("BTC/USDT", small, small, small)
    assert signal.accepted is False
    assert signal.reason == "INSUFFICIENT_DATA"


def test_signal_contains_three_screens():
    frame = make_frame(100, 0.1)
    signal = evaluate("BTC/USDT", frame, frame, frame)
    assert signal.tide.state in {"bull", "bear", "neutral"}
    assert signal.wave.state in {"pullback", "extended"}
    assert signal.ripple.state in {"up", "down"}
    assert 0 <= signal.score <= 1
