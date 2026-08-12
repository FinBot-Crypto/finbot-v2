"""
fb-core-monitor: Monitora posições v2 e executa política de exit do payload.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import math
import os
import time
import uuid

import ccxt
import nats
import numpy as np
import psycopg2
from nats.js.api import ConsumerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fb-core-monitor")

NATS_URL = os.getenv("NATS_URL", "nats://crypto-nats:4222")
DATABASE_URL = os.getenv("DATABASE_URL", "")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "10"))
RSI_PERIOD = 56
BNB_MIN_USD = float(os.getenv("BNB_MIN_USD", "5"))
BNB_TARGET_USD = float(os.getenv("BNB_TARGET_USD", "10"))
DUST_INTERVAL = int(os.getenv("DUST_INTERVAL", "21600"))


class CoreMonitorService:
    def __init__(self):
        self.nc = None
        self.js = None
        self.kv = None
        self.positions: dict[str, dict] = {}
        opts = {
            "apiKey": BINANCE_API_KEY,
            "secret": BINANCE_API_SECRET,
            "enableRateLimit": True,
            "timeout": 15000,
        }
        self.spot = ccxt.binance(opts)
        self.futures = ccxt.binance({**opts, "options": {"defaultType": "future"}})

    async def connect_nats(self):
        self.nc = await nats.connect(NATS_URL)
        self.js = self.nc.jetstream()
        self.kv = await self.js.key_value("active_positions")
        logger.info("NATS conectado: %s", NATS_URL)

    def _kv_key(self, pos: dict) -> str:
        raw = f"{pos['block_id']}:{pos['symbol']}:{pos['direction']}:{pos['venue']}"
        return base64.b64encode(raw.encode()).decode()

    def _exchange(self, venue: str):
        return self.futures if venue == "futures" else self.spot

    def _ccxt_symbol(self, symbol: str, venue: str) -> str:
        if venue == "futures" and ":" not in symbol:
            return f"{symbol}:USDT"
        return symbol

    async def load_positions_from_kv(self):
        self.positions = {}
        try:
            keys = await self.kv.keys()
            for key in keys:
                entry = await self.kv.get(key)
                pos = json.loads(entry.value.decode())
                self.positions[key] = pos
        except Exception as exc:
            logger.error("Erro load KV: %s", exc)

    def compute_rsi(self, closes):
        delta = np.diff(closes)
        gain = np.maximum(delta, 0)
        loss = -np.minimum(delta, 0)
        avg_gain = np.convolve(gain, np.ones(RSI_PERIOD) / RSI_PERIOD, mode="valid")
        avg_loss = np.convolve(loss, np.ones(RSI_PERIOD) / RSI_PERIOD, mode="valid")
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - 100 / (1 + rs)
        return float(rsi[-1])

    async def check_position(self, pos: dict) -> dict | None:
        symbol = pos["symbol"]
        venue = pos.get("venue", "spot")
        direction = pos.get("direction", "LONG")
        is_short = direction == "SHORT"
        exchange = self._exchange(venue)
        ccxt_symbol = self._ccxt_symbol(symbol, venue)

        try:
            ticker = exchange.fetch_ticker(ccxt_symbol)
            current_price = ticker["last"]
        except Exception as exc:
            logger.error("Ticker %s: %s", symbol, exc)
            return None

        entry_price = float(pos["entry_price"])
        exit_cfg = pos.get("exit") or {}
        sl_price = float(exit_cfg.get("sl_price") or pos.get("sl_price") or 0)
        tp_price = float(exit_cfg.get("tp_price") or pos.get("tp_price") or 0)
        max_hold = float(exit_cfg.get("max_hold_hours", 12))
        rsi_exit = float(exit_cfg.get("rsi_exit", 70))
        trailing = exit_cfg.get("trailing") or {}

        pnl_pct = (1 - current_price / entry_price) * 100 if is_short else (current_price / entry_price - 1) * 100
        entry_time = pos.get("opened_at") or pos.get("entry_time") or time.time()
        if isinstance(entry_time, str):
            entry_time = time.time()
        hold_hours = (time.time() - float(entry_time)) / 3600

        if sl_price > 0:
            if is_short and current_price >= sl_price:
                return {"reason": "STOP_LOSS", "price": current_price, "pnl_pct": pnl_pct}
            if not is_short and current_price <= sl_price:
                return {"reason": "STOP_LOSS", "price": current_price, "pnl_pct": pnl_pct}

        if tp_price > 0:
            if is_short and current_price <= tp_price:
                return {"reason": "TAKE_PROFIT", "price": current_price, "pnl_pct": pnl_pct}
            if not is_short and current_price >= tp_price:
                return {"reason": "TAKE_PROFIT", "price": current_price, "pnl_pct": pnl_pct}

        if hold_hours >= max_hold:
            return {"reason": "TIME_EXIT", "price": current_price, "pnl_pct": pnl_pct}

        if 0 < rsi_exit < 100:
            try:
                ohlcv = exchange.fetch_ohlcv(ccxt_symbol, "15m", limit=200)
                closes = [c[4] for c in ohlcv]
                if len(closes) >= RSI_PERIOD + 1:
                    rsi = self.compute_rsi(closes)
                    if is_short and rsi <= (100 - rsi_exit):
                        return {"reason": "RSI_REVERSAL", "price": current_price, "pnl_pct": pnl_pct}
                    if not is_short and rsi >= rsi_exit:
                        return {"reason": "RSI_REVERSAL", "price": current_price, "pnl_pct": pnl_pct}
            except Exception as exc:
                logger.error("RSI %s: %s", symbol, exc)

        if sl_price > 0 and trailing.get("enabled"):
            try:
                ohlcv = exchange.fetch_ohlcv(ccxt_symbol, "15m", limit=50)
                highs = [c[2] for c in ohlcv]
                lows = [c[3] for c in ohlcv]
                tr_closes = [c[4] for c in ohlcv]
                tr = np.maximum.reduce(
                    [
                        np.array(highs[1:]) - np.array(lows[1:]),
                        np.abs(np.array(highs[1:]) - np.array(tr_closes[:-1])),
                        np.abs(np.array(lows[1:]) - np.array(tr_closes[:-1])),
                    ]
                )
                atr = float(np.mean(tr[-14:])) if len(tr) >= 14 else 0.01
                activation = float(trailing.get("activation_atr", 1.0))
                distance = float(trailing.get("distance_atr", 2.0))

                if is_short:
                    profit_atr = (entry_price - current_price) / atr if atr > 0 else 0
                    if profit_atr >= activation:
                        new_sl = current_price + distance * atr
                        old_sl = float(pos.get("sl_price") or exit_cfg.get("sl_price") or 99999999)
                        if new_sl < old_sl:
                            pos["sl_price"] = new_sl
                            exit_cfg["sl_price"] = new_sl
                            pos["exit"] = exit_cfg
                            pos["trailing_active"] = True
                            await self.kv.put(self._kv_key(pos), json.dumps(pos).encode())
                else:
                    profit_atr = (current_price - entry_price) / atr if atr > 0 else 0
                    if profit_atr >= activation:
                        new_sl = current_price - distance * atr
                        old_sl = float(pos.get("sl_price") or exit_cfg.get("sl_price") or 0)
                        if new_sl > old_sl:
                            pos["sl_price"] = new_sl
                            exit_cfg["sl_price"] = new_sl
                            pos["exit"] = exit_cfg
                            pos["trailing_active"] = True
                            await self.kv.put(self._kv_key(pos), json.dumps(pos).encode())
            except Exception as exc:
                logger.error("Trailing %s: %s", symbol, exc)

        return None

    def log_open(self, opened: dict):
        if not DATABASE_URL:
            return
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO positions (
                    id, block_id, client_order_id, strategy, symbol, direction, tier,
                    venue, leverage, entry_type, entry_price, quantity, quantity_exit,
                    sl_price, tp_price, exit_config, signal_meta, status, exchange_order_id, dry_run
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s
                )
                """,
                (
                    opened.get("order_id") or str(uuid.uuid4()),
                    opened["block_id"],
                    opened.get("client_order_id"),
                    opened["strategy"],
                    opened["symbol"],
                    opened["direction"],
                    opened.get("tier"),
                    opened["venue"],
                    opened.get("leverage", 1),
                    opened.get("entry", {}).get("type", "market"),
                    opened["entry_price"],
                    opened.get("quantity_filled") or opened.get("quantity"),
                    opened.get("quantity_exit") or opened.get("quantity_filled"),
                    opened.get("exit", {}).get("sl_price"),
                    opened.get("exit", {}).get("tp_price"),
                    json.dumps(opened.get("exit", {})),
                    json.dumps(opened.get("signal", {})),
                    "OPEN",
                    opened.get("exchange_order_id"),
                    opened.get("dry_run", DRY_RUN),
                ),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as exc:
            logger.error("DB open %s: %s", opened.get("symbol"), exc)

    def log_close(self, pos: dict, reason_data: dict):
        if not DATABASE_URL:
            return
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            hold_hours = (time.time() - float(pos.get("opened_at") or time.time())) / 3600
            cur.execute(
                """
                UPDATE positions SET
                    status = 'CLOSED',
                    exit_price = %s,
                    exit_reason = %s,
                    pnl_pct = %s,
                    hold_hours = %s,
                    closed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    reason_data["price"],
                    reason_data["reason"],
                    round(reason_data["pnl_pct"], 4),
                    round(hold_hours, 2),
                    pos.get("order_id"),
                ),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as exc:
            logger.error("DB close %s: %s", pos.get("symbol"), exc)

    async def close_position(self, pos: dict, reason_data: dict):
        symbol = pos["symbol"]
        logger.info(
            "FECHANDO %s [%s] %s @ %.6f PnL=%.2f%%",
            symbol,
            pos.get("block_id"),
            reason_data["reason"],
            reason_data["price"],
            reason_data["pnl_pct"],
        )

        if not DRY_RUN and reason_data["reason"] != "EXCHANGE_CLOSED":
            payload = json.dumps(
                {
                    "block_id": pos["block_id"],
                    "symbol": symbol,
                    "direction": pos.get("direction", "LONG"),
                    "venue": pos.get("venue", "spot"),
                    "order_id": pos.get("order_id"),
                }
            ).encode()
            await self.js.publish("trade.close", payload)

        key = self._kv_key(pos)
        if DRY_RUN or reason_data["reason"] == "EXCHANGE_CLOSED":
            try:
                await self.kv.delete(key)
            except Exception:
                pass

        self.log_close(pos, reason_data)
        if key in self.positions:
            del self.positions[key]

        closed = {
            "block_id": pos.get("block_id"),
            "order_id": pos.get("order_id"),
            "symbol": symbol,
            "tier": pos.get("tier"),
            "strategy": pos.get("strategy"),
            "direction": pos.get("direction"),
            "venue": pos.get("venue"),
            "entry_price": pos.get("entry_price"),
            "exit_price": reason_data["price"],
            "quantity": pos.get("quantity_exit") or pos.get("quantity_filled"),
            "exit_reason": reason_data["reason"],
            "pnl_pct": round(reason_data["pnl_pct"], 2),
            "hold_hours": round((time.time() - float(pos.get("opened_at") or time.time())) / 3600, 2),
            "leverage": pos.get("leverage", 1),
            "client_order_id": pos.get("client_order_id"),
            "timestamp": time.time(),
        }
        await self.js.publish("trade.closed", json.dumps(closed).encode())

    async def process_opened(self, msg):
        try:
            opened = json.loads(msg.data.decode())
            opened["opened_at"] = time.time()
            key = self._kv_key(opened)
            self.positions[key] = opened
            await self.kv.put(key, json.dumps(opened).encode())
            self.log_open(opened)
            logger.info("POSIÇÃO ABERTA: %s %s %s", opened["block_id"], opened["symbol"], opened["direction"])
            await msg.ack()
        except Exception as exc:
            logger.error("Erro trade.opened: %s", exc)

    async def monitor_loop(self):
        logger.info("fb-core-monitor online (interval=%ss)", MONITOR_INTERVAL)
        dust_counter = 0
        while True:
            if self.nc.is_closed:
                await self.connect_nats()
                await self.load_positions_from_kv()

            for key, pos in list(self.positions.items()):
                result = await self.check_position(pos)
                if result:
                    await self.close_position(pos, result)

            dust_counter += MONITOR_INTERVAL
            if dust_counter >= DUST_INTERVAL:
                dust_counter = 0

            await asyncio.sleep(MONITOR_INTERVAL)

    async def run(self):
        await self.connect_nats()
        await self.load_positions_from_kv()
        await self.js.subscribe(
            "trade.opened",
            durable="CORE_MONITOR_OPENED",
            cb=self.process_opened,
            manual_ack=True,
            config=ConsumerConfig(ack_wait=30),
        )
        await self.monitor_loop()


if __name__ == "__main__":
    asyncio.run(CoreMonitorService().run())
