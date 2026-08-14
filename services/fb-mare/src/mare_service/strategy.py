from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .indicators import atr, ema, rsi


@dataclass(frozen=True)
class Screen:
    state: str
    score: float
    value: float
    reason: str


@dataclass(frozen=True)
class MareSignal:
    symbol: str
    direction: str | None
    score: float
    accepted: bool
    reason: str
    tide: Screen
    wave: Screen
    ripple: Screen
    price: float
    atr: float

    def as_dict(self) -> dict:
        data = asdict(self)
        return data


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _trend_screen(frame: pd.DataFrame) -> Screen:
    close = frame["close"]
    fast = ema(close, 20).iloc[-1]
    slow = ema(close, 50).iloc[-1]
    macd_fast = ema(close, 12)
    macd_slow = ema(close, 26)
    histogram = (macd_fast - macd_slow) - ema(macd_fast - macd_slow, 9)
    hist = float(histogram.iloc[-1])
    volatility = float(close.pct_change().rolling(20).std().iloc[-1])
    if not pd.notna(volatility):
        volatility = 0.0
    scale = max(float(close.iloc[-1]) * 0.002, volatility * float(close.iloc[-1]))
    spread = (float(fast) - float(slow)) / max(scale, 1e-12)
    trend_score = _bounded(0.5 + spread / 8.0)
    if spread > 0.35 and hist >= 0:
        state = "bull"
    elif spread < -0.35 and hist <= 0:
        state = "bear"
    else:
        state = "neutral"
    return Screen(state, trend_score, spread, f"EMA20/EMA50 spread={spread:.3f}, MACD-H={hist:.6g}")


def _wave_screen(frame: pd.DataFrame, direction: str) -> Screen:
    close = frame["close"]
    current_rsi = float(rsi(close).iloc[-1])
    middle = float(ema(close, 20).iloc[-1])
    distance = (float(close.iloc[-1]) / max(middle, 1e-12)) - 1.0
    if direction == "LONG":
        pullback = _bounded(1.0 - abs(current_rsi - 45.0) / 30.0)
        state = "pullback" if current_rsi <= 55 and distance <= 0.01 else "extended"
    else:
        pullback = _bounded(1.0 - abs(current_rsi - 55.0) / 30.0)
        state = "pullback" if current_rsi >= 45 and distance >= -0.01 else "extended"
    return Screen(state, pullback, current_rsi, f"RSI14={current_rsi:.2f}, EMA20 distance={distance:.4%}")


def _ripple_screen(frame: pd.DataFrame, direction: str) -> Screen:
    close = frame["close"]
    fast = ema(close, 9)
    momentum = float(close.iloc[-1] / close.iloc[-4] - 1.0)
    recent_high = float(frame["high"].iloc[-4:-1].max())
    recent_low = float(frame["low"].iloc[-4:-1].min())
    if direction == "LONG":
        trigger = float(close.iloc[-1]) > recent_high and float(fast.iloc[-1]) > float(fast.iloc[-2])
        state = "up" if trigger else "down"
        score = _bounded(0.5 + momentum * 20.0)
    else:
        trigger = float(close.iloc[-1]) < recent_low and float(fast.iloc[-1]) < float(fast.iloc[-2])
        state = "down" if trigger else "up"
        score = _bounded(0.5 - momentum * 20.0)
    return Screen(state, score, momentum, f"momentum4={momentum:.4%}, trigger={trigger}")


def evaluate(symbol: str, tide_frame: pd.DataFrame, wave_frame: pd.DataFrame, ripple_frame: pd.DataFrame, min_score: float = 0.65) -> MareSignal:
    if min(map(len, (tide_frame, wave_frame, ripple_frame))) < 60:
        neutral = Screen("neutral", 0.0, 0.0, "insufficient candles")
        return MareSignal(symbol, None, 0.0, False, "INSUFFICIENT_DATA", neutral, neutral, neutral, float(ripple_frame["close"].iloc[-1]), 0.0)

    tide = _trend_screen(tide_frame)
    candidates: list[tuple[str, Screen, Screen, float, bool]] = []
    for direction, expected_tide, expected_ripple in (("LONG", "bull", "up"), ("SHORT", "bear", "down")):
        wave = _wave_screen(wave_frame, direction)
        ripple = _ripple_screen(ripple_frame, direction)
        score = 0.50 * tide.score + 0.25 * wave.score + 0.25 * ripple.score
        aligned = tide.state == expected_tide and wave.state == "pullback" and ripple.state == expected_ripple
        candidates.append((direction, wave, ripple, score, aligned))

    aligned_candidates = [item for item in candidates if item[4]]
    selected = max(aligned_candidates or candidates, key=lambda item: item[3])
    direction, wave, ripple, raw_score, aligned = selected
    score = round(raw_score, 4)
    accepted = aligned and score >= min_score
    reason = "ACCEPTED" if accepted else "NO_ALIGNMENT"
    current_atr = float(atr(ripple_frame).iloc[-1])
    return MareSignal(symbol, direction if accepted else None, score, accepted, reason, tide, wave, ripple, float(ripple_frame["close"].iloc[-1]), current_atr)
