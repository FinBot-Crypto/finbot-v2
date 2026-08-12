from __future__ import annotations


def calc_leverage(score: float, min_score: float, pct_2x: float, pct_3x: float, pct_5x: float) -> int:
    t_5x = min_score + (1.0 - min_score) * pct_5x
    t_3x = min_score + (1.0 - min_score) * pct_3x
    t_2x = min_score + (1.0 - min_score) * pct_2x
    if score >= t_5x:
        return 5
    if score >= t_3x:
        return 3
    if score >= t_2x:
        return 2
    return 1


def calc_sl_tp_prices(
    current_price: float,
    direction: str,
    sl_pct: float,
    tp_pct: float,
) -> tuple[float, float]:
    is_short = direction.upper() == "SHORT"
    if is_short:
        tp_price = current_price * (1.0 - tp_pct)
        sl_price = current_price * (1.0 + sl_pct)
    else:
        tp_price = current_price * (1.0 + tp_pct)
        sl_price = current_price * (1.0 - sl_pct)
    return sl_price, tp_price
