from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import psycopg2
import os
import json
import base64
import nats
import ccxt
import asyncio
import time as _time

app = FastAPI(title="FinBot v2 Dashboard")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://crypto_admin:ZNG5z43LaSrk7FEmwu6CPtRUB2IVKdvY@crypto-postgres:5432/crypto_bot",
)
NATS_URL = os.getenv("NATS_URL", "nats://crypto-nats:4222")
DEFAULT_BLOCK = "leme"

TZ_EXPR = "AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo'"


def get_db_conn():
    return psycopg2.connect(DATABASE_URL)


def _parse_jsonb(value):
    if value is None:
        return None
    if isinstance(value, (dict, list, bool, int, float)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


_nats_client = None


async def get_nats():
    global _nats_client
    if _nats_client is None or _nats_client.is_closed:
        _nats_client = await nats.connect(NATS_URL)
    return _nats_client


_cached_spot_ex = None
_cached_futures_ex = None


def _get_spot_ex():
    global _cached_spot_ex
    if _cached_spot_ex is None:
        api_key = os.getenv("BINANCE_API_KEY")
        secret = os.getenv("BINANCE_API_SECRET")
        config = {
            "enableRateLimit": True,
            "timeout": 15000,
        }
        if api_key and api_key not in ("your_api_key", ""):
            config["apiKey"] = api_key
        if secret and secret not in ("your_api_secret", ""):
            config["secret"] = secret
        _cached_spot_ex = ccxt.binance(config)
    return _cached_spot_ex


def _get_futures_ex():
    global _cached_futures_ex
    if _cached_futures_ex is None:
        api_key = os.getenv("BINANCE_API_KEY")
        secret = os.getenv("BINANCE_API_SECRET")
        config = {
            "enableRateLimit": True,
            "timeout": 15000,
            "options": {"defaultType": "future"},
        }
        if api_key and api_key not in ("your_api_key", ""):
            config["apiKey"] = api_key
        if secret and secret not in ("your_api_secret", ""):
            config["secret"] = secret
        _cached_futures_ex = ccxt.binance(config)
    return _cached_futures_ex


def _get_binance_balances(spot_ex, futures_ex):
    spot_total, spot_free, spot_used, bnb_usd = 0.0, 0.0, 0.0, 0.0
    futures_total, futures_free, futures_used = 0.0, 0.0, 0.0
    try:
        spot_bal = spot_ex.fetch_balance()
        spot_free = float(spot_bal.get("USDT", {}).get("free", 0.0))
        total_val_usdt = spot_bal["total"].get("USDT", 0.0)
        for asset, amount in spot_bal["total"].items():
            if amount > 0 and asset != "USDT":
                try:
                    if asset == "BNB":
                        total_val_usdt += amount * spot_ex.fetch_ticker("BNB/USDT")["last"]
                    else:
                        ticker = spot_ex.fetch_ticker(f"{asset}/USDT")
                        total_val_usdt += amount * ticker["last"]
                except Exception:
                    pass
        spot_total = round(total_val_usdt, 2)

        bnb_amount = spot_bal["total"].get("BNB", 0.0)
        if bnb_amount > 0:
            try:
                bnb_usd = round(bnb_amount * spot_ex.fetch_ticker("BNB/USDT")["last"], 2)
            except Exception:
                pass

        spot_used = round(spot_total - spot_free - bnb_usd, 2)
        if spot_used < 0:
            spot_used = 0.0
    except Exception as e:
        print(f"[PERF] ERRO ao buscar saldos Spot: {e}")

    try:
        f_bal = futures_ex.fetch_balance()
        usdt_info = f_bal.get("USDT", {})
        futures_total = float(usdt_info.get("total", 0.0))
        futures_free = float(usdt_info.get("free", 0.0))
        futures_used = float(usdt_info.get("used", 0.0))
    except Exception as e:
        print(f"[PERF] ERRO ao buscar saldos Futures: {e}")

    return {
        "total": spot_total,
        "free": spot_free,
        "used": spot_used,
        "bnb_usd": bnb_usd,
    }, {
        "total": futures_total,
        "free": futures_free,
        "used": futures_used,
    }


def _fetch_all_binance_data(symbols_to_fetch):
    current_prices = {}
    t0 = _time.time()
    if symbols_to_fetch:
        try:
            tickers = _get_spot_ex().fetch_tickers(symbols_to_fetch)
            for sym in symbols_to_fetch:
                if sym in tickers:
                    current_prices[sym] = tickers[sym].get("last")
        except Exception as e:
            print(f"[PERF] ERRO fetch_tickers: {e}")

    spot_balances, futures_balances = _get_binance_balances(_get_spot_ex(), _get_futures_ex())
    print(f"[PERF] _fetch_all_binance_data TOTAL: {(_time.time() - t0) * 1000:.0f}ms")
    return current_prices, spot_balances, futures_balances


def _fetch_dashboard_binance_data():
    t0 = _time.time()
    spot_balances, futures_balances = _get_binance_balances(_get_spot_ex(), _get_futures_ex())
    print(f"[PERF] _fetch_dashboard_binance_data TOTAL: {(_time.time() - t0) * 1000:.0f}ms")
    return spot_balances, futures_balances


def _kv_key(block_id, symbol, direction, venue):
    raw = f"{block_id}:{symbol}:{direction}:{venue}"
    return base64.b64encode(raw.encode()).decode()


def _fetch_block_settings(cur, block_id):
    cur.execute(
        "SELECT key, value FROM block_settings WHERE block_id = %s",
        (block_id,),
    )
    return {k: _parse_jsonb(v) for k, v in cur.fetchall()}


def _fetch_global_settings(cur):
    cur.execute("SELECT key, value FROM global_settings")
    return {k: _parse_jsonb(v) for k, v in cur.fetchall()}


def _validate_setting_key(key, value):
    if "min_score" in key:
        val = float(value)
        if val <= 0 or val >= 1.0:
            raise HTTPException(status_code=400, detail=f"Score mínimo para {key} deve ser entre 0.0 e 1.0")
    elif key.endswith("_sl") or key.endswith("_tp") or ".sl" in key or ".tp" in key:
        val = float(value)
        if val <= 0 or val > 100.0:
            raise HTTPException(status_code=400, detail=f"SL/TP para {key} deve ser entre 0.1% e 100%")
    elif "rsi" in key:
        val = float(value)
        if val <= 0 or val > 100.0:
            raise HTTPException(status_code=400, detail=f"RSI para {key} deve ser entre 1 e 100")
    elif "allowed_regimes" in key:
        if not isinstance(value, list):
            raise HTTPException(status_code=400, detail=f"Regimes para {key} deve ser uma lista")
        for regime in value:
            if regime not in ("bull", "bear", "neutral"):
                raise HTTPException(status_code=400, detail=f"Regime inválido: {regime}")
    elif key.endswith("_enabled") or key == "dry_run":
        if not isinstance(value, bool):
            raise HTTPException(status_code=400, detail=f"{key} deve ser booleano")
    elif "win_rate" in key or "winrate" in key:
        val = float(value)
        if val < 0 or val > 100.0:
            raise HTTPException(status_code=400, detail=f"{key} deve ser entre 0% e 100%")
    elif "cooldown_hours" in key or "max_hold_hours" in key:
        val = float(value)
        if val <= 0 or val > 720:
            raise HTTPException(status_code=400, detail=f"{key} deve ser entre 1 e 720 horas")
    elif "max_consecutive_sl" in key or "shadow_min_trades" in key or "max_positions" in key:
        val = int(value)
        if val <= 0 or val > 100:
            raise HTTPException(status_code=400, detail=f"{key} deve ser um inteiro positivo razoável")


@app.get("/api/dashboard")
async def get_dashboard_data():
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute(
            f"""
            SELECT symbol, pnl_pct, entry_price, quantity,
                   closed_at {TZ_EXPR}
            FROM positions
            WHERE status = 'CLOSED'
            ORDER BY closed_at ASC NULLS LAST
            """
        )
        rows = cur.fetchall()

        total_closed = len(rows)
        wins = 0
        losses = 0
        total_pnl_money = 0.0
        curve_data = []
        coin_stats = {}

        for symbol, pnl_pct, entry_price, quantity, closed_at in rows:
            if pnl_pct is not None and entry_price is not None and quantity is not None:
                invested = float(entry_price) * float(quantity)
                pnl_money = (float(pnl_pct) / 100) * invested
                total_pnl_money += pnl_money

                if pnl_pct > 0:
                    wins += 1
                else:
                    losses += 1

                curve_data.append(
                    {
                        "date": closed_at.strftime("%d/%m") if closed_at else "",
                        "pnl": round(total_pnl_money, 2),
                    }
                )

                if symbol not in coin_stats:
                    coin_stats[symbol] = {"symbol": symbol, "pnl": 0, "wins": 0, "losses": 0, "total": 0}
                coin_stats[symbol]["pnl"] += pnl_money
                coin_stats[symbol]["total"] += 1
                if pnl_pct > 0:
                    coin_stats[symbol]["wins"] += 1
                else:
                    coin_stats[symbol]["losses"] += 1

        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

        best_coins = sorted(coin_stats.values(), key=lambda x: x["pnl"], reverse=True)[:5]
        worst_coins = sorted(coin_stats.values(), key=lambda x: x["pnl"])[:5]
        most_traded = sorted(coin_stats.values(), key=lambda x: x["total"], reverse=True)[:5]

        cur.execute(
            f"""
            SELECT symbol, entry_price, quantity, opened_at {TZ_EXPR}
            FROM positions WHERE status = 'OPEN'
            """
        )
        active_positions = [
            {
                "symbol": r[0],
                "entry_price": float(r[1]) if r[1] is not None else None,
                "quantity": float(r[2]) if r[2] is not None else None,
                "created_at": r[3].strftime("%d/%m %H:%M") if r[3] else "",
            }
            for r in cur.fetchall()
        ]

        cur.execute(
            "SELECT block_id, allocated_usdt, realized_pnl FROM block_budgets ORDER BY block_id"
        )
        budgets = {
            r[0]: {
                "allocated_usdt": float(r[1]) if r[1] is not None else 0.0,
                "realized_pnl": float(r[2]) if r[2] is not None else 0.0,
            }
            for r in cur.fetchall()
        }

        cur.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

    spot_balances, futures_balances = await asyncio.to_thread(_fetch_dashboard_binance_data)

    return {
        "total_pnl_money": round(total_pnl_money, 2),
        "win_rate": round(win_rate, 1),
        "total_closed": total_closed,
        "wins": wins,
        "losses": losses,
        "active_positions": active_positions,
        "budgets": budgets,
        "patrimony": round(spot_balances["total"] + futures_balances["total"], 2),
        "spot_balance": round(spot_balances["total"], 2),
        "spot_balance_free": round(spot_balances["free"], 2),
        "spot_balance_used": round(spot_balances["used"], 2),
        "futures_balance": round(futures_balances["total"], 2),
        "futures_balance_free": round(futures_balances["free"], 2),
        "futures_balance_used": round(futures_balances["used"], 2),
        "bnb_balance": spot_balances["bnb_usd"],
        "rankings": {
            "best": [{"symbol": x["symbol"], "pnl": round(x["pnl"], 2)} for x in best_coins],
            "worst": [{"symbol": x["symbol"], "pnl": round(x["pnl"], 2)} for x in worst_coins],
            "most_traded": [
                {"symbol": x["symbol"], "wins": x["wins"], "losses": x["losses"], "total": x["total"]}
                for x in most_traded
            ],
        },
        "curve": curve_data,
    }


@app.get("/api/operations")
async def get_operations(page: int = 1, limit: int = 50):
    t_start = _time.time()
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM positions WHERE status = 'CLOSED'")
        total_closed = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM positions WHERE status = 'OPEN'")
        total_open = cur.fetchone()[0]

        offset = (page - 1) * limit
        cur.execute(
            f"""
            SELECT id, block_id, client_order_id, symbol, status, entry_price, exit_price, quantity,
                   exit_reason, pnl_pct,
                   opened_at {TZ_EXPR},
                   COALESCE(closed_at, updated_at) {TZ_EXPR},
                   venue, leverage, signal_meta, direction, tier, sl_price, tp_price, strategy
            FROM positions
            ORDER BY opened_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()

        cur.execute(
            """
            SELECT symbol, COUNT(*) as total,
                   SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END) as losses
            FROM positions WHERE status = 'CLOSED'
            GROUP BY symbol
            """
        )
        coin_wl = {r[0]: {"total": r[1], "wins": r[2] or 0, "losses": r[3] or 0} for r in cur.fetchall()}

        cur.execute(
            """
            SELECT COALESCE(SUM((pnl_pct/100) * entry_price * quantity), 0)
            FROM positions
            WHERE status = 'CLOSED' AND entry_price IS NOT NULL AND quantity IS NOT NULL
            """
        )
        total_pnl = round(float(cur.fetchone()[0]), 2)

        cur.execute(
            f"""
            SELECT tier,
                   date(COALESCE(closed_at, updated_at) {TZ_EXPR}) as day,
                   COUNT(*) as total,
                   SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_pct <= 0 THEN 1 ELSE 0 END) as losses,
                   COALESCE(SUM((pnl_pct/100) * entry_price * quantity), 0) as pnl_money
            FROM positions
            WHERE status = 'CLOSED' AND entry_price IS NOT NULL AND quantity IS NOT NULL
            GROUP BY tier, day
            ORDER BY day DESC, tier
            """
        )
        tier_by_day = {}
        for tier_name, day, total, w, l, pnl_money in cur.fetchall():
            day_str = day.strftime("%d/%m") if day else ""
            tier_by_day.setdefault(day_str, []).append(
                {
                    "tier": tier_name or "Desconhecido",
                    "total": total,
                    "wins": w or 0,
                    "losses": l or 0,
                    "pnl_money": round(float(pnl_money), 4),
                }
            )

        block_settings = _fetch_block_settings(cur, DEFAULT_BLOCK)
        cur.close()
    except Exception as e:
        import traceback

        print(f"[PERF] /api/operations ERRO DB: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

    t_db = _time.time()
    print(f"[PERF] DB queries: {(t_db - t_start) * 1000:.0f}ms")

    kv_by_client = {}
    kv_by_composite = {}
    kv_by_symbol = {}
    symbols_to_fetch = []
    try:
        nc = await get_nats()
        js = nc.jetstream()
        kv = await asyncio.wait_for(js.key_value("active_positions"), timeout=2.0)
        keys = await kv.keys()

        for k in keys:
            try:
                entry = await kv.get(k)
                if not entry:
                    continue
                pos = json.loads(entry.value.decode())
                sym = pos.get("symbol", "")
                if sym:
                    symbols_to_fetch.append(sym)

                exit_cfg = pos.get("exit") or {}
                info = {
                    "sl_price": pos.get("sl_price") or exit_cfg.get("sl_price"),
                    "tp_price": pos.get("tp_price") or exit_cfg.get("tp_price"),
                    "entry_time": pos.get("entry_time") or pos.get("opened_at"),
                    "is_futures": pos.get("venue") == "futures",
                    "leverage": pos.get("leverage", 1),
                    "score": (pos.get("signal") or {}).get("score"),
                    "rsi": (pos.get("signal") or {}).get("rsi"),
                }

                client_id = pos.get("client_order_id")
                if client_id:
                    kv_by_client[client_id] = info
                composite = _kv_key(
                    pos.get("block_id", DEFAULT_BLOCK),
                    sym,
                    str(pos.get("direction", "LONG")).upper(),
                    pos.get("venue", "spot"),
                )
                kv_by_composite[composite] = info
                if sym:
                    kv_by_symbol[sym] = info
            except Exception as entry_err:
                print(f"[PERF] Erro KV key: {entry_err}")
    except Exception as e:
        print(f"[PERF] Erro KV: {e}")

    binance_prices, spot_balances, futures_balances = await asyncio.to_thread(
        _fetch_all_binance_data, list(set(symbols_to_fetch))
    )

    open_orders = []
    closed_orders = []

    for row in rows:
        (
            pid,
            block_id,
            client_order_id,
            symbol,
            status,
            entry_price,
            exit_price,
            quantity,
            exit_reason,
            pnl_pct,
            opened_at,
            closed_at,
            venue,
            leverage,
            signal_meta,
            direction,
            tier,
            sl_price,
            tp_price,
            strategy,
        ) = row

        meta = _parse_jsonb(signal_meta) or {}
        order = {
            "id": str(pid),
            "block_id": block_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "status": status,
            "entry_price": float(entry_price) if entry_price is not None else None,
            "exit_price": float(exit_price) if exit_price is not None else None,
            "quantity": float(quantity) if quantity is not None else None,
            "exit_reason": exit_reason,
            "pnl_pct": float(pnl_pct) if pnl_pct is not None else None,
            "created_at": opened_at.strftime("%d/%m %H:%M") if opened_at else "",
            "updated_at": closed_at.strftime("%d/%m %H:%M") if closed_at else "",
            "venue": venue,
            "is_futures": venue == "futures",
            "leverage": leverage or 1,
            "score": meta.get("score"),
            "rsi": meta.get("rsi"),
            "direction": direction or "LONG",
            "tier": tier,
            "strategy": strategy,
            "sl_price": float(sl_price) if sl_price is not None else None,
            "tp_price": float(tp_price) if tp_price is not None else None,
        }

        if status == "OPEN":
            kv_info = (
                kv_by_client.get(client_order_id)
                or kv_by_composite.get(_kv_key(block_id, symbol, direction or "LONG", venue or "spot"))
                or kv_by_symbol.get(symbol, {})
            )
            order["sl_price"] = kv_info.get("sl_price", order["sl_price"])
            order["tp_price"] = kv_info.get("tp_price", order["tp_price"])
            order["entry_time"] = kv_info.get("entry_time")
            order["is_futures"] = kv_info.get("is_futures", order["is_futures"])
            order["leverage"] = kv_info.get("leverage", order["leverage"])
            if kv_info.get("score") is not None:
                order["score"] = kv_info["score"]
            if kv_info.get("rsi") is not None:
                order["rsi"] = kv_info["rsi"]

            price = binance_prices.get(symbol)
            if price is None and "/" not in symbol:
                price = binance_prices.get(symbol + "/USDT")
            order["current_price"] = price

            wl = coin_wl.get(symbol, {})
            order["coin_wins"] = wl.get("wins", 0)
            order["coin_losses"] = wl.get("losses", 0)
            order["coin_total"] = wl.get("total", 0)
            open_orders.append(order)
        else:
            closed_orders.append(order)

    max_hold_hours = float(
        block_settings.get("exit.max_hold_hours", os.getenv("MAX_HOLD_HOURS", "12"))
    )

    print(
        f"[PERF] /api/operations TOTAL: {(_time.time() - t_start) * 1000:.0f}ms "
        f"(open={len(open_orders)}, closed={len(closed_orders)})"
    )

    return {
        "open": open_orders,
        "closed": closed_orders,
        "total_open": total_open,
        "total_closed": total_closed,
        "total_pnl": total_pnl,
        "page": page,
        "limit": limit,
        "max_hold_hours": max_hold_hours,
        "tier_by_day": tier_by_day,
        "spot_balance": round(spot_balances["total"], 2),
        "spot_balance_free": round(spot_balances["free"], 2),
        "spot_balance_used": round(spot_balances["used"], 2),
        "futures_balance": round(futures_balances["total"], 2),
        "futures_balance_free": round(futures_balances["free"], 2),
        "futures_balance_used": round(futures_balances["used"], 2),
        "bnb_balance": round(spot_balances["bnb_usd"], 2),
    }


def aggregate_shadow_simulations(rows, direction="LONG"):
    if not rows:
        return {
            "total_simulations": 0,
            "ranking_sltp": [],
            "ranking_rsi": [],
            "ranking_hour": [],
            "ranking_symbol": [],
            "ranking_tier": [],
            "ranking_trend": [],
            "best_combo": None,
            "best_scores": [],
        }

    sltp_agg = {}
    rsi_agg = {}
    hour_agg = {h: {"pnls": []} for h in range(24)}
    symbol_agg = {}
    combo_agg = {}
    tier_agg = {}
    trend_agg = {
        "bull": {"trend": "bull", "pnls": []},
        "bear": {"trend": "bear", "pnls": []},
        "neutral": {"trend": "neutral", "pnls": []},
    }
    window_agg = {
        "Madrugada (0–6h)": {"window": "Madrugada (0–6h)", "pnls": []},
        "Manhã (6–12h)": {"window": "Manhã (6–12h)", "pnls": []},
        "Tarde (12–18h)": {"window": "Tarde (12–18h)", "pnls": []},
        "Noite (18–24h)": {"window": "Noite (18–24h)", "pnls": []},
    }
    score_details = []

    for row in rows:
        symbol, tier, rsi_e, hour_e, entry_price, sl, tp, pnl, reason, minutes, ms, bt = row

        tier = tier or "Desconhecido"
        hour_e = int(hour_e) if hour_e is not None else None
        rsi_e = float(rsi_e) if rsi_e else None
        pnl = float(pnl) if pnl else 0
        model_score = float(ms) if ms is not None else None
        btc_trend = bt or "neutral"

        sltp_key = f"SL={sl or 'Nulo'} | TP={tp or 'Nulo'}"
        sltp_agg.setdefault(sltp_key, {"config": sltp_key, "sl": sl, "tp": tp, "pnls": []})
        sltp_agg[sltp_key]["pnls"].append(pnl)

        rl = None
        if rsi_e is not None:
            if direction == "SHORT":
                if rsi_e >= 75:
                    rl = ">=75"
                elif rsi_e >= 70:
                    rl = "70-75"
                else:
                    rl = "65-70"
            else:
                if rsi_e < 25:
                    rl = "<25"
                elif rsi_e < 30:
                    rl = "25-30"
                elif rsi_e < 35:
                    rl = "30-35"
                else:
                    rl = "35+"
            rsi_agg.setdefault(rl, {"pnls": []})
            rsi_agg[rl]["pnls"].append(pnl)

        if hour_e is not None:
            hour_agg[hour_e]["pnls"].append(pnl)
            if 0 <= hour_e < 6:
                wl = "Madrugada (0–6h)"
            elif 6 <= hour_e < 12:
                wl = "Manhã (6–12h)"
            elif 12 <= hour_e < 18:
                wl = "Tarde (12–18h)"
            else:
                wl = "Noite (18–24h)"
            window_agg[wl]["pnls"].append(pnl)

        symbol_agg.setdefault(symbol, {"pnls": [], "count": 0})
        symbol_agg[symbol]["pnls"].append(pnl)
        symbol_agg[symbol]["count"] += 1

        if rsi_e is not None and hour_e is not None and rl:
            win = (
                "Madrugada"
                if 0 <= hour_e < 6
                else "Manha"
                if 6 <= hour_e < 12
                else "Tarde"
                if 12 <= hour_e < 18
                else "Noite"
            )
            combo_key = f"RSI {rl} | {win}"
            combo_agg.setdefault(combo_key, {"label": combo_key, "pnls": []})
            combo_agg[combo_key]["pnls"].append(pnl)

        tier_agg.setdefault(tier, {"tier": tier, "pnls": []})
        tier_agg[tier]["pnls"].append(pnl)

        trend_agg.setdefault(btc_trend, {"trend": btc_trend, "pnls": []})
        trend_agg[btc_trend]["pnls"].append(pnl)

        if model_score is not None:
            score_details.append(
                {
                    "symbol": symbol,
                    "score": model_score,
                    "rsi": rsi_e,
                    "hour": hour_e,
                    "pnl": pnl,
                    "sl": sl,
                    "tp": tp,
                    "reason": reason,
                }
            )

    def fmt_agg(agg_dict, label_key, limit=15):
        out = []
        for v in agg_dict.values():
            pnls = v["pnls"]
            n = len(pnls)
            if n == 0:
                item = {"avg_pnl": 0, "win_rate": 0, "count": 0}
            else:
                avg = sum(pnls) / n
                wins = sum(1 for p in pnls if p > 0)
                item = {"avg_pnl": round(avg, 3), "win_rate": round(wins / n * 100, 1), "count": n}
            if label_key in v:
                item[label_key] = v[label_key]
            out.append(item)
        out.sort(key=lambda x: x["avg_pnl"], reverse=True)
        return out[:limit]

    ranking_sltp = fmt_agg(sltp_agg, "config")

    ranking_rsi = []
    rsi_keys = [">=75", "70-75", "65-70"] if direction == "SHORT" else ["<25", "25-30", "30-35", "35+"]
    for key in rsi_keys:
        if key in rsi_agg:
            pnls = rsi_agg[key]["pnls"]
            n = len(pnls)
            if n > 0:
                avg = sum(pnls) / n
                wins = sum(1 for p in pnls if p > 0)
                ranking_rsi.append(
                    {"range": key, "avg_pnl": round(avg, 3), "win_rate": round(wins / n * 100, 1), "count": n}
                )
        else:
            ranking_rsi.append({"range": key, "avg_pnl": 0, "win_rate": 0, "count": 0})

    ranking_hour = []
    for h in range(24):
        ps = hour_agg[h]["pnls"]
        avg = round(sum(ps) / len(ps), 3) if ps else None
        ranking_hour.append({"hour": h, "avg_pnl": avg, "count": len(ps)})

    ranking_hour_windows = []
    for wl in ["Madrugada (0–6h)", "Manhã (6–12h)", "Tarde (12–18h)", "Noite (18–24h)"]:
        ps = window_agg[wl]["pnls"]
        n = len(ps)
        if n > 0:
            avg = sum(ps) / n
            wins = sum(1 for p in ps if p > 0)
            ranking_hour_windows.append(
                {"window": wl, "avg_pnl": round(avg, 3), "win_rate": round(wins / n * 100, 1), "count": n}
            )
        else:
            ranking_hour_windows.append({"window": wl, "avg_pnl": 0, "win_rate": 0, "count": 0})

    ranking_symbol = fmt_agg(symbol_agg, "symbol")
    ranking_tier = fmt_agg(tier_agg, "tier")
    ranking_trend = fmt_agg(trend_agg, "trend")

    best_combo = None
    candidates = []
    for v in combo_agg.values():
        pnls = v["pnls"]
        n = len(pnls)
        if n < 3:
            continue
        avg = sum(pnls) / n
        wins = sum(1 for p in pnls if p > 0)
        candidates.append(
            {"label": v["label"], "avg_pnl": round(avg, 3), "win_rate": round(wins / n * 100, 1), "count": n}
        )
    if candidates:
        candidates.sort(key=lambda x: x["avg_pnl"], reverse=True)
        best_combo = candidates[0]

    score_details.sort(key=lambda x: x["score"], reverse=True)
    seen = set()
    best_scores = []
    for sd in score_details:
        key = (sd["symbol"], round(sd["score"], 4))
        if key not in seen:
            seen.add(key)
            best_scores.append(sd)
            if len(best_scores) >= 10:
                break

    return {
        "total_simulations": len(rows),
        "ranking_sltp": ranking_sltp,
        "ranking_rsi": ranking_rsi,
        "ranking_hour": ranking_hour,
        "ranking_hour_windows": ranking_hour_windows,
        "ranking_symbol": ranking_symbol,
        "ranking_tier": ranking_tier,
        "ranking_trend": ranking_trend,
        "best_combo": best_combo,
        "best_scores": best_scores,
    }


def _fetch_shadow_rows(table, min_model_score, include_trend=False):
    cols = "symbol, tier, rsi_entry, hour_entry, entry_price, sl, tp, pnl, exit_reason, minutes, model_score"
    if include_trend:
        cols += ", btc_trend"
    conn = get_db_conn()
    try:
        cur = conn.cursor()
        if min_model_score > 0:
            cur.execute(
                f"""
                SELECT {cols}
                FROM {table}
                WHERE model_score IS NOT NULL AND model_score >= %s
                ORDER BY entry_ts DESC
                """,
                (min_model_score,),
            )
        else:
            cur.execute(f"SELECT {cols} FROM {table} ORDER BY entry_ts DESC")
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def _empty_shadow_tiers():
    empty = {
        "total_simulations": 0,
        "ranking_sltp": [],
        "ranking_rsi": [],
        "ranking_hour": [],
        "ranking_symbol": [],
        "best_combo": None,
        "best_scores": [],
    }
    return {
        **empty,
        "ranking_tier": [],
        "ranking_trend": [],
        "tiers": {
            "Major": {**empty},
            "Strong Alt": {**empty},
            "High Volatility": {**empty},
        },
    }


@app.get("/api/shadow-short")
async def get_shadow_short_metrics(min_model_score: float = 0):
    try:
        rows = _fetch_shadow_rows("leme_shadow_short", min_model_score, include_trend=True)
        if not rows:
            return _empty_shadow_tiers()

        rows_by_tier = {"Major": [], "Strong Alt": [], "High Volatility": []}
        for row in rows:
            tier = row[1] or "Desconhecido"
            if tier in rows_by_tier:
                rows_by_tier[tier].append(row)

        tier_metrics = {t: aggregate_shadow_simulations(t_rows, "SHORT") for t, t_rows in rows_by_tier.items()}
        return {**aggregate_shadow_simulations(rows, "SHORT"), "tiers": tier_metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shadow-long-scan")
async def get_shadow_long_scan(min_model_score: float = 0):
    try:
        rows = _fetch_shadow_rows("leme_shadow_long", min_model_score, include_trend=False)
        if not rows:
            return {
                "total_simulations": 0,
                "ranking_sltp": [],
                "ranking_rsi": [],
                "ranking_hour": [],
                "ranking_tier": [],
                "ranking_symbol": [],
                "ranking_trend": [],
                "best_combo": None,
            }

        sltp_agg, tier_agg, symbol_agg = {}, {}, {}
        rsi_agg = {}
        hour_agg = {h: {"pnls": []} for h in range(24)}
        for row in rows:
            symbol, tier, rsi_e, hour_e, entry_price, sl, tp, pnl, reason, minutes, ms = row
            tier = tier or "Desconhecido"
            pnl = float(pnl) if pnl else 0
            rsi_e = float(rsi_e) if rsi_e else None
            hour_e = int(hour_e) if hour_e is not None else None
            sltp_key = f"SL={sl or 'Nulo'} | TP={tp or 'Nulo'}"
            sltp_agg.setdefault(sltp_key, {"config": sltp_key, "sl": sl, "tp": tp, "pnls": []})
            sltp_agg[sltp_key]["pnls"].append(pnl)
            tier_agg.setdefault(tier, {"tier": tier, "pnls": []})
            tier_agg[tier]["pnls"].append(pnl)
            if rsi_e is not None:
                if rsi_e < 25:
                    rl = "<25"
                elif rsi_e < 30:
                    rl = "25-30"
                elif rsi_e < 35:
                    rl = "30-35"
                else:
                    rl = "35+"
                rsi_agg.setdefault(rl, {"pnls": []})
                rsi_agg[rl]["pnls"].append(pnl)
            if hour_e is not None:
                hour_agg[hour_e]["pnls"].append(pnl)
            symbol_agg.setdefault(symbol, {"symbol": symbol, "pnls": []})
            symbol_agg[symbol]["pnls"].append(pnl)

        def fmt(agg, key, lim=15):
            out = []
            for v in agg.values():
                pnls = v["pnls"]
                if len(pnls) < 5:
                    continue
                avg = sum(pnls) / len(pnls)
                wins = sum(1 for p in pnls if p > 0)
                out.append(
                    {
                        "avg_pnl": round(avg, 3),
                        "win_rate": round(wins / len(pnls) * 100, 1),
                        "count": len(pnls),
                        key: v.get(key, ""),
                    }
                )
            out.sort(key=lambda x: x["avg_pnl"], reverse=True)
            return out[:lim]

        rsltp = fmt(sltp_agg, "config")
        rtier = fmt(tier_agg, "tier")
        rsym = fmt(symbol_agg, "symbol")
        r_rsi = []
        for k in ["<25", "25-30", "30-35", "35+"]:
            pnls = rsi_agg.get(k, {"pnls": []})["pnls"]
            n = len(pnls)
            a = sum(pnls) / n if n > 0 else 0
            w = sum(1 for p in pnls if p > 0)
            r_rsi.append(
                {"range": k, "avg_pnl": round(a, 3), "win_rate": round(w / n * 100, 1) if n else 0, "count": n}
            )
        rhour = [
            {
                "hour": h,
                "avg_pnl": round(sum(p) / len(p), 3) if (p := hour_agg[h]["pnls"]) else None,
                "count": len(p),
            }
            for h in range(24)
        ]
        return {
            "total_simulations": sum(len(v["pnls"]) for v in sltp_agg.values()),
            "ranking_sltp": rsltp,
            "ranking_rsi": r_rsi,
            "ranking_hour": rhour,
            "ranking_tier": rtier,
            "ranking_symbol": rsym,
            "best_combo": rsltp[0] if rsltp else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/shadow")
async def get_shadow_metrics(min_model_score: float = 0.73):
    """Alias for frontend — full tier breakdown from leme_shadow_long."""
    try:
        rows = _fetch_shadow_rows("leme_shadow_long", min_model_score, include_trend=True)
        if not rows:
            return _empty_shadow_tiers()

        rows_by_tier = {"Major": [], "Strong Alt": [], "High Volatility": []}
        for row in rows:
            tier = row[1] or "Desconhecido"
            if tier in rows_by_tier:
                rows_by_tier[tier].append(row)

        tier_metrics = {t: aggregate_shadow_simulations(t_rows, "LONG") for t, t_rows in rows_by_tier.items()}
        return {**aggregate_shadow_simulations(rows, "LONG"), "tiers": tier_metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/btc-trend")
async def get_btc_trend():
    try:
        exchange = ccxt.binance({"enableRateLimit": True})
        period = int(os.getenv("BTC_SMA_PERIOD", "12"))
        ohlcv = exchange.fetch_ohlcv("BTC/USDT", "1h", limit=period + 10)
        if not ohlcv or len(ohlcv) < period:
            return {"trend": "neutral", "btc_price": 0, "sma": 0}
        closes = [c[4] for c in ohlcv]
        sma = sum(closes[-period:]) / period
        current = closes[-1]
        pct = (current / sma - 1) * 100
        if current > sma * 1.01:
            trend = "bull"
        elif current < sma * 0.99:
            trend = "bear"
        else:
            trend = "neutral"
        return {"trend": trend, "btc_price": round(current, 2), "sma": round(sma, 2), "pct": round(pct, 2)}
    except Exception as e:
        return {"trend": "neutral", "error": str(e)}


V2_SERVICES = [
    "fb-leme-scan",
    "fb-leme-engine",
    "fb-leme-guardian",
    "fb-leme-shadow",
    "fb-core-exec",
    "fb-core-monitor",
    "fb-core-dashboard",
    "crypto-nats",
    "crypto-postgres",
]


@app.get("/api/status")
async def get_status():
    services = []
    db_ok = False
    conn = None
    try:
        conn = get_db_conn()
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        if conn:
            conn.close()

    try:
        import docker as dk

        client = dk.from_env()
        for name in V2_SERVICES:
            if name == "crypto-postgres":
                services.append({"name": name, "status": "Online" if db_ok else "Offline"})
                continue
            try:
                container = client.containers.get(name)
                running = container.status == "running"
                services.append({"name": name, "status": "Online" if running else "Offline"})
            except Exception:
                services.append({"name": name, "status": "Offline"})
    except Exception:
        for name in V2_SERVICES:
            if name == "crypto-postgres":
                services.append({"name": name, "status": "Online" if db_ok else "Offline"})
            else:
                services.append({"name": name, "status": "Online" if db_ok else "Offline"})

    return {"services": services}


@app.get("/api/settings")
async def get_bot_settings(block: str = Query(DEFAULT_BLOCK)):
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        block_settings = _fetch_block_settings(cur, block)
        global_settings = _fetch_global_settings(cur)
        cur.close()
        merged = {**global_settings, **block_settings}
        merged["_meta"] = {"block": block, "global_keys": list(global_settings.keys())}
        return merged
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.post("/api/settings")
async def update_bot_settings(payload: dict, block: str = Query(DEFAULT_BLOCK)):
    conn = None
    try:
        updates = {k: v for k, v in payload.items() if not k.startswith("_")}
        for k, v in updates.items():
            _validate_setting_key(k, v)

        conn = get_db_conn()
        cur = conn.cursor()
        for k, v in updates.items():
            cur.execute(
                """
                INSERT INTO block_settings (block_id, key, value, updated_at)
                VALUES (%s, %s, %s::jsonb, CURRENT_TIMESTAMP)
                ON CONFLICT (block_id, key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """,
                (block, k, json.dumps(v)),
            )
        conn.commit()
        cur.close()
        return {"status": "success", "message": "Configurações salvas.", "block": block}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.get("/api/leme/history")
async def get_leme_history(block: str = Query(DEFAULT_BLOCK)):
    conn = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, block_id, action, reason, scope,
                   created_at {TZ_EXPR} as created_at
            FROM guardian_events
            WHERE block_id = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (block,),
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "block_id": r[1],
                "group_name": r[4],
                "action": r[2],
                "reason": r[3],
                "scope": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


if os.path.exists("./dist"):
    app.mount("/assets", StaticFiles(directory="./dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = f"./dist/{full_path}" if full_path else "./dist/index.html"
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("./dist/index.html")
else:

    @app.get("/")
    def read_root():
        return {"message": "FinBot v2 API. Frontend não buildado (rode npm run build)."}
