"""
fb-core-exec: Executa trade.order (spot + futures unificado).

Fluxo:
  trade.order → valida payload → entry market/limit → trade.opened
  trade.close → fecha posição na exchange
"""
from __future__ import annotations

import asyncio
import base64
import decimal
import json
import logging
import math
import os
import time

import ccxt
import nats
from finbot_common.payloads import TradeOpened, validate_trade_order
from nats.js.api import ConsumerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fb-core-exec")

NATS_URL = os.getenv("NATS_URL", "nats://crypto-nats:4222")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "20"))


class CoreExecService:
    def __init__(self):
        self.nc = None
        self.js = None
        self.kv = None
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

    def _kv_key(self, order: dict) -> str:
        raw = f"{order['block_id']}:{order['symbol']}:{order['direction']}:{order['venue']}"
        return base64.b64encode(raw.encode()).decode()

    def _exchange(self, venue: str):
        return self.futures if venue == "futures" else self.spot

    def _ccxt_symbol(self, symbol: str, venue: str) -> str:
        if venue == "futures" and ":" not in symbol:
            return f"{symbol}:USDT"
        return symbol

    async def position_exists(self, order: dict) -> bool:
        try:
            await self.kv.get(self._kv_key(order))
            return True
        except Exception:
            return False

    async def count_positions(self) -> int:
        try:
            keys = await self.kv.keys()
            return len(keys)
        except Exception:
            return 0

    def _resolve_qty_after_fill(self, exchange, symbol: str, venue: str, filled_qty: float) -> float:
        if venue == "futures":
            qty_str = exchange.amount_to_precision(self._ccxt_symbol(symbol, venue), filled_qty)
            return float(qty_str)
        try:
            bal = exchange.fetch_balance()
            base = symbol.split("/")[0]
            actual = bal["free"].get(base, filled_qty)
            qty_str = exchange.amount_to_precision(symbol, actual)
            sell_qty = float(qty_str)
            if sell_qty <= 0:
                sell_qty = float(exchange.amount_to_precision(symbol, filled_qty))
            return sell_qty
        except Exception:
            return filled_qty

    def _place_oco_spot(self, exchange, order: dict, sell_qty: float) -> str | None:
        exit_cfg = order["exit"]
        sl_price = exit_cfg["sl_price"]
        tp_price = exit_cfg["tp_price"]
        symbol = order["symbol"]
        exec_cfg = order.get("execution", {})
        max_retries = int(exec_cfg.get("max_retries", 3))
        retry_delay = int(exec_cfg.get("retry_delay_sec", 1))
        on_fail = exec_cfg.get("on_oco_failure", "market_close")

        market_info = exchange.market(symbol)
        price_step = market_info["precision"]["price"]
        price_decimals = max(0, -int(round(math.log10(price_step))))
        tp_str = format(decimal.Decimal(str(round(tp_price, price_decimals))), "f")
        sl_str = format(decimal.Decimal(str(round(sl_price, price_decimals))), "f")

        for attempt in range(max_retries):
            try:
                oco_qty_str = exchange.amount_to_precision(symbol, sell_qty)
                result = exchange.private_post_order_oco(
                    {
                        "symbol": symbol.replace("/", ""),
                        "side": "SELL",
                        "quantity": oco_qty_str,
                        "price": tp_str,
                        "stopPrice": sl_str,
                        "stopLimitPrice": sl_str,
                        "stopLimitTimeInForce": "GTC",
                    }
                )
                return str(result.get("orderListId"))
            except Exception as exc:
                logger.error("%s OCO falhou (%s/%s): %s", symbol, attempt + 1, max_retries, exc)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                elif on_fail == "market_close":
                    try:
                        bal = exchange.fetch_balance()
                        base = symbol.split("/")[0]
                        free_qty = bal["free"].get(base, sell_qty)
                        qty_str = exchange.amount_to_precision(symbol, free_qty)
                        if float(qty_str) > 0:
                            exchange.create_order(symbol, "market", "sell", qty_str)
                    except Exception as sell_err:
                        logger.error("%s erro market_close pós-OCO: %s", symbol, sell_err)
        return None

    async def _wait_limit_fill(self, exchange, symbol: str, order_id: str, timeout_sec: int) -> dict | None:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                o = exchange.fetch_order(order_id, symbol)
                status = o.get("status")
                if status == "closed":
                    return o
                if status == "canceled":
                    return None
            except Exception as exc:
                logger.error("Erro polling limit %s: %s", symbol, exc)
            await asyncio.sleep(2)
        try:
            exchange.cancel_order(order_id, symbol)
        except Exception:
            pass
        return None

    async def execute_order(self, raw: dict) -> dict | None:
        try:
            order = validate_trade_order(raw)
        except ValueError as exc:
            logger.error("Payload inválido: %s", exc)
            return None

        if await self.position_exists(order):
            logger.info("%s já aberto (%s)", order["symbol"], order["block_id"])
            return None

        if await self.count_positions() >= MAX_POSITIONS:
            logger.info("Max posições atingido (%s)", MAX_POSITIONS)
            return None

        venue = order["venue"]
        symbol = order["symbol"]
        direction = order["direction"]
        is_short = direction == "SHORT"
        exchange = self._exchange(venue)
        ccxt_symbol = self._ccxt_symbol(symbol, venue)
        side = "sell" if is_short else "buy"
        qty_requested = float(order["quantity"])
        client_order_id = order["client_order_id"]
        entry = order["entry"]
        exit_cfg = order["exit"]

        if DRY_RUN:
            entry_price = float(entry.get("price") or order.get("notional_usdt", 0) / max(qty_requested, 1e-9))
            opened = TradeOpened.from_order(
                order,
                entry_price=entry_price,
                quantity_requested=qty_requested,
                quantity_filled=qty_requested,
                quantity_exit=qty_requested,
                exchange_order_id="dry_run",
            )
            opened["dry_run"] = True
            await self.kv.put(self._kv_key(order), json.dumps(opened).encode())
            return opened

        try:
            if venue == "futures":
                try:
                    exchange.set_margin_mode("ISOLATED", ccxt_symbol)
                except Exception:
                    pass
                leverage = int(order.get("leverage", 1))
                try:
                    exchange.set_leverage(leverage, ccxt_symbol)
                except Exception as exc:
                    logger.warning("%s leverage: %s", symbol, exc)

            params = {"newClientOrderId": client_order_id[:36]}
            entry_type = entry["type"]

            if entry_type == "limit":
                limit_price = entry.get("price")
                if not limit_price:
                    logger.error("%s limit sem price", symbol)
                    return None
                limit_order = exchange.create_order(
                    ccxt_symbol if venue == "futures" else symbol,
                    "limit",
                    side,
                    qty_requested,
                    limit_price,
                    params=params,
                )
                timeout = int(entry.get("timeout_sec") or 60)
                filled = await self._wait_limit_fill(
                    exchange,
                    ccxt_symbol if venue == "futures" else symbol,
                    limit_order["id"],
                    timeout,
                )
                if not filled:
                    fallback = entry.get("fallback", "abort")
                    if fallback == "market":
                        buy_order = exchange.create_order(
                            ccxt_symbol if venue == "futures" else symbol,
                            "market",
                            side,
                            qty_requested,
                            params={"newClientOrderId": f"{client_order_id[:30]}-m"},
                        )
                    else:
                        logger.info("%s limit expirou — abort", symbol)
                        return None
                else:
                    buy_order = filled
            else:
                buy_order = exchange.create_order(
                    ccxt_symbol if venue == "futures" else symbol,
                    "market",
                    side,
                    qty_requested,
                    params=params,
                )

            filled_price = float(buy_order.get("average") or buy_order.get("price") or 0)
            filled_qty = float(buy_order.get("filled") or qty_requested)
            qty_exit = self._resolve_qty_after_fill(exchange, symbol, venue, filled_qty)

            if venue == "spot" and exit_cfg.get("mode") == "exchange_oco" and not is_short:
                self._place_oco_spot(exchange, order, qty_exit)

            opened = TradeOpened.from_order(
                order,
                entry_price=filled_price,
                quantity_requested=qty_requested,
                quantity_filled=filled_qty,
                quantity_exit=qty_exit,
                exchange_order_id=str(buy_order.get("id")),
            )
            opened["dry_run"] = False
            await self.kv.put(self._kv_key(order), json.dumps(opened).encode())
            logger.info(
                "%s opened %s %s @ %s qty=%s",
                order["block_id"],
                direction,
                symbol,
                filled_price,
                qty_exit,
            )
            return opened

        except ccxt.InsufficientFunds as exc:
            logger.error("%s saldo insuficiente: %s", symbol, exc)
            return None
        except Exception as exc:
            logger.error("%s erro execução: %s", symbol, exc)
            return None

    async def close_position(self, msg):
        try:
            data = json.loads(msg.data.decode())
            block_id = data["block_id"]
            symbol = data["symbol"]
            direction = data.get("direction", "LONG")
            venue = data.get("venue", "spot")
            key_raw = f"{block_id}:{symbol}:{direction}:{venue}"
            key = base64.b64encode(key_raw.encode()).decode()

            try:
                entry = await self.kv.get(key)
                pos = json.loads(entry.value.decode())
            except Exception:
                await msg.ack()
                return

            qty = float(pos.get("quantity_exit") or pos.get("quantity", 0))
            exchange = self._exchange(venue)
            ccxt_symbol = self._ccxt_symbol(symbol, venue)
            is_short = direction == "SHORT"
            side = "buy" if is_short else "sell"

            if DRY_RUN:
                await self.kv.delete(key)
                await msg.ack()
                return

            params = {"reduceOnly": True} if venue == "futures" else {}
            close_cid = f"{pos.get('client_order_id', 'FB')[:28]}-c"
            params["newClientOrderId"] = close_cid[:36]
            qty_str = exchange.amount_to_precision(ccxt_symbol, qty)
            exchange.create_order(ccxt_symbol, "market", side, qty_str, params=params)
            await self.kv.delete(key)
            await msg.ack()
        except Exception as exc:
            logger.error("Erro close: %s", exc)

    async def process_order(self, msg):
        try:
            raw = json.loads(msg.data.decode())
            orders = raw if isinstance(raw, list) else [raw]
            for item in orders:
                opened = await self.execute_order(item)
                if opened:
                    await self.js.publish("trade.opened", json.dumps(opened).encode())
            await msg.ack()
        except Exception as exc:
            logger.error("Erro process_order: %s", exc)

    async def run(self):
        await self.connect_nats()
        await self.js.subscribe(
            "trade.order",
            durable="CORE_EXEC_WORKER",
            cb=self.process_order,
            manual_ack=True,
            config=ConsumerConfig(ack_wait=60),
        )
        await self.js.subscribe(
            "trade.close",
            durable="CORE_EXEC_CLOSE_WORKER",
            cb=self.close_position,
            manual_ack=True,
            config=ConsumerConfig(ack_wait=30),
        )
        mode = "DRY RUN" if DRY_RUN else "PRODUÇÃO"
        logger.info("fb-core-exec online [%s]", mode)
        while True:
            if self.nc.is_closed:
                await self.connect_nats()
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(CoreExecService().run())
