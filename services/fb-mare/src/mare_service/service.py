from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import ccxt
import nats
import pandas as pd
from nats.js.api import ConsumerConfig

from .config import Config
from .indicators import ohlcv_frame
from .orders import build_order
from .repository import Repository
from .strategy import evaluate

try:
    from finbot_common.payloads import validate_trade_order
except ModuleNotFoundError:
    validate_trade_order = None


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fb-mare")


class MareService:
    def __init__(self, config: Config | None = None, exchange=None):
        self.config = config or Config()
        self.repository = Repository(self.config.database_url)
        self.exchange = exchange or ccxt.binance({"enableRateLimit": True, "timeout": 15000})
        self.nc = None
        self.js = None
        self.last_event = None

    async def connect(self):
        self.nc = await nats.connect(self.config.nats_url)
        self.js = self.nc.jetstream()
        logger.info("fb-mare online: input=%s live_orders=%s", self.config.universe_subject, self.config.live_orders_enabled)

    async def fetch(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        rows = await asyncio.to_thread(self.exchange.fetch_ohlcv, symbol, timeframe, limit=limit)
        return ohlcv_frame(rows)

    async def analyze_asset(self, asset: dict, block_enabled: bool, settings: dict) -> dict | None:
        symbol = asset.get("symbol")
        if not symbol:
            return None
        try:
            tide, wave, ripple = await asyncio.gather(
                self.fetch(symbol, self.config.tide_timeframe, self.config.max_tide_candles),
                self.fetch(symbol, self.config.wave_timeframe, self.config.max_wave_candles),
                self.fetch(symbol, self.config.ripple_timeframe, self.config.max_ripple_candles),
            )
            signal = evaluate(symbol, tide, wave, ripple, self.config.min_score)
            payload = signal.as_dict()
            db_live_enabled = settings.get("mare.live_orders_enabled", False)
            if isinstance(db_live_enabled, str):
                db_live_enabled = db_live_enabled.lower() in {"1", "true", "yes", "on"}
            live_enabled = block_enabled and self.config.live_orders_enabled and bool(db_live_enabled)
            self.repository.save_signal(payload, block_enabled, live_enabled)
            if signal.accepted and live_enabled:
                order = build_order(signal, self.config.notional_usdt)
                if validate_trade_order:
                    validate_trade_order(order)
                await self.js.publish("trade.order", json.dumps(order).encode())
                logger.warning("MARE ORDER published: %s %s score=%.3f", signal.direction, symbol, signal.score)
            elif signal.accepted:
                logger.info("MARE SHADOW signal: %s %s score=%.3f block_enabled=%s", signal.direction, symbol, signal.score, block_enabled)
            return payload
        except Exception as exc:
            logger.error("%s analysis failed: %s", symbol, exc)
            return None

    async def process_universe(self, msg):
        try:
            body = json.loads(msg.data.decode())
            assets = body.get("assets", body) if isinstance(body, (dict, list)) else []
            if not isinstance(assets, list):
                assets = []
            assets = assets[: self.config.max_assets_per_cycle]
            settings = self.repository.settings()
            block_enabled = self.repository.block_enabled()
            logger.info("Analyzing %d assets [mare_enabled=%s]", len(assets), block_enabled)
            results = await asyncio.gather(*(self.analyze_asset(asset, block_enabled, settings) for asset in assets))
            accepted = sum(1 for result in results if result and result.get("accepted"))
            logger.info("Cycle complete: %d/%d accepted by screens; live publishing=%s", accepted, len(assets), block_enabled and self.config.live_orders_enabled)
            await msg.ack()
        except Exception:
            logger.exception("Error processing %s", self.config.universe_subject)

    async def run(self):
        await self.connect()
        await self.js.subscribe(
            self.config.universe_subject,
            durable="MARE_ENGINE_WORKER",
            cb=self.process_universe,
            manual_ack=True,
            config=ConsumerConfig(
                ack_wait=self.config.cycle_timeout_sec,
                max_ack_pending=1,
            ),
            pending_msgs_limit=1,
        )
        while True:
            if self.nc.is_closed:
                await self.connect()
            await asyncio.sleep(10)


def main():
    asyncio.run(MareService().run())
