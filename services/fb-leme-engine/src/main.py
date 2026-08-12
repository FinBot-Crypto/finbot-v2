"""
fb-leme-engine: LSTM scoring + entry filters + order sizing (FinBot v2).

Fluxo:
  leme.universe → LSTM score → filtros (regime, RSI, cooldown) → trade.order
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time

import ccxt
import nats
import numpy as np
import pandas as pd
import psycopg2
import torch
import torch.nn as nn
from finbot_common.client_order_id import build_client_order_id
from finbot_common.db import fetch_block_settings
from finbot_common.indicators import compute_atr, compute_rsi_smooth
from finbot_common.payloads import TradeOrder
from finbot_common.risk import calc_leverage, calc_sl_tp_prices
from finbot_common.settings import entry_allowed_key, get_bool, get_float, get_int
from nats.js.api import ConsumerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fb-leme-engine")

NATS_URL = os.getenv("NATS_URL", "nats://crypto-nats:4222")
DATABASE_URL = os.getenv("DATABASE_URL", "")
MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")
BLOCK_ID = "leme"

SEQ_LEN = 144
RSI_PERIOD = 56
MIN_CANDLES = 200
ATR_PERIOD = 14

MODEL_FILES = {
    "Major": "model_mean_reversion_v1_lstm_Major.pt",
    "Strong Alt": "model_mean_reversion_v1_lstm_StrongAlt.pt",
    "High Volatility": "model_mean_reversion_v1_lstm_HighVolatility.pt",
}

SHORT_MODEL_FILES = {
    "Major": "model_short_lstm_Major.pt",
    "Strong Alt": "model_short_lstm_StrongAlt.pt",
    "High Volatility": "model_short_lstm_HighVolatility.pt",
}

_PLACEHOLDER_KEYS = {"", "your_api_key", "your_api_secret"}
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
_api_key = BINANCE_API_KEY if BINANCE_API_KEY not in _PLACEHOLDER_KEYS else None
_api_secret = BINANCE_API_SECRET if BINANCE_API_SECRET not in _PLACEHOLDER_KEYS else None


def tier_slug(tier: str) -> str:
    return tier.lower().replace(" ", "_")


def entry_key(direction: str, tier: str, suffix: str) -> str:
    return f"entry.{direction.lower()}_{tier_slug(tier)}_{suffix}"


class LSTMMeanReversion(nn.Module):
    def __init__(self, input_size=3, hidden_size=128, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return torch.sigmoid(self.fc(lstm_out[:, -1, :]))


class LemeEngine:
    def __init__(self):
        self.nc = None
        self.js = None
        self.kv = None
        self.models: dict = {}
        self.short_models: dict = {}
        self.settings: dict = {}
        self.last_settings_update = 0.0
        self.db_conn = None
        self.db_cursor = None
        self.active_futures_count = 0

        _opts: dict = {"enableRateLimit": True, "timeout": 15000}
        if _api_key:
            _opts["apiKey"] = _api_key
            _opts["secret"] = _api_secret
        self.spot_exchange = ccxt.binance(_opts)
        self.futures_exchange = ccxt.binance({**_opts, "options": {"defaultType": "future"}})
        self.exchange = self.spot_exchange
        self._futures_ex = self.futures_exchange

        try:
            self.spot_exchange.load_markets()
            self.futures_exchange.load_markets()
        except Exception as exc:
            logger.warning("Mercados Binance indisponíveis no boot: %s", exc)

        self._load_models()

    def _load_models(self):
        for tier, fname in MODEL_FILES.items():
            path = os.path.join(MODELS_DIR, fname)
            if not os.path.exists(path):
                logger.warning("Modelo LONG não encontrado: %s", path)
                continue
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            cfg = ckpt.get("config", {})
            nf = cfg.get("n_features", 3)
            model = LSTMMeanReversion(nf, cfg.get("hidden", 128), cfg.get("layers", 1))
            model.load_state_dict(ckpt["model_state_dict"])
            model.eval()
            self.models[tier] = {
                "model": model,
                "seq_len": cfg.get("seq_len", SEQ_LEN),
                "n_features": nf,
            }
            logger.info("Modelo LONG carregado: %s (%s) nf=%s", tier, fname, nf)

        for tier, fname in SHORT_MODEL_FILES.items():
            path = os.path.join(MODELS_DIR, fname)
            if not os.path.exists(path):
                logger.warning("Modelo SHORT não encontrado: %s", path)
                continue
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            cfg = ckpt.get("config", {})
            nf = cfg.get("n_features", 3)
            model = LSTMMeanReversion(nf, cfg.get("hidden", 128), cfg.get("layers", 1))
            model.load_state_dict(ckpt["model_state_dict"])
            model.eval()
            self.short_models[tier] = {
                "model": model,
                "seq_len": cfg.get("seq_len", SEQ_LEN),
                "n_features": nf,
            }
            logger.info("Modelo SHORT carregado: %s (%s) nf=%s", tier, fname, nf)

    async def connect_nats(self):
        while True:
            try:
                self.nc = await nats.connect(NATS_URL)
                self.js = self.nc.jetstream()
                try:
                    self.kv = await self.js.key_value("active_positions")
                except Exception as exc:
                    logger.warning("KV active_positions indisponível: %s", exc)
                    self.kv = None
                logger.info("NATS conectado: %s", NATS_URL)
                return
            except Exception as exc:
                logger.error("Erro NATS: %s — retry em 5s", exc)
                await asyncio.sleep(5)

    def _ensure_db(self):
        if self.db_conn is None or self.db_conn.closed != 0:
            self.db_conn = psycopg2.connect(DATABASE_URL)
            self.db_conn.autocommit = True
            self.db_cursor = self.db_conn.cursor()

    def get_settings(self) -> dict:
        now = time.time()
        if now - self.last_settings_update > 30 or not self.settings:
            try:
                self._ensure_db()
                self.settings = fetch_block_settings(self.db_conn, BLOCK_ID)
                self.last_settings_update = now
                logger.debug("block_settings recarregadas (%s chaves)", len(self.settings))
            except Exception as exc:
                logger.error("Erro ao carregar block_settings: %s", exc)
        return self.settings

    def log_evaluation(
        self,
        symbol: str,
        tier: str,
        strategy: str,
        direction: str,
        score: float | None,
        rsi: float | None,
        regime: str,
        decision: str,
    ):
        if not DATABASE_URL:
            return
        try:
            self._ensure_db()
            self.db_cursor.execute(
                """
                INSERT INTO evaluations_log
                    (block_id, symbol, tier, strategy, direction, score, rsi, regime, decision)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (BLOCK_ID, symbol, tier, strategy, direction, score, rsi, regime, decision),
            )
        except Exception as exc:
            logger.error("Erro ao salvar evaluations_log: %s", exc)
            self.db_conn = None
            self.db_cursor = None

    def is_in_cooldown(self, symbol: str, cooldown_hours: float) -> bool:
        if cooldown_hours <= 0 or not DATABASE_URL:
            return False
        try:
            self._ensure_db()
            self.db_cursor.execute(
                """
                SELECT pnl_pct, EXTRACT(EPOCH FROM closed_at), exit_reason
                FROM positions
                WHERE block_id = %s AND symbol = %s AND status = 'CLOSED'
                ORDER BY closed_at DESC LIMIT 10
                """,
                (BLOCK_ID, symbol),
            )
            rows = self.db_cursor.fetchall()
            if not rows:
                return False

            consecutive_losses = 0
            last_exit_ts = None
            for pnl_pct, closed_ts, exit_reason in rows:
                if last_exit_ts is None:
                    last_exit_ts = float(closed_ts or 0)
                pnl = float(pnl_pct) if pnl_pct is not None else 0.0
                if pnl < 0 or exit_reason == "STOP_LOSS":
                    consecutive_losses += 1
                else:
                    break

            if consecutive_losses > 0 and last_exit_ts:
                cooldown_h = min(cooldown_hours * (2.0 ** (consecutive_losses - 1)), 48.0)
                elapsed = time.time() - last_exit_ts
                if elapsed < cooldown_h * 3600:
                    logger.info(
                        "  [COOLDOWN] %s: %s loss(es) — %.1fh < %.1fh",
                        symbol,
                        consecutive_losses,
                        elapsed / 3600,
                        cooldown_h,
                    )
                    return True
        except Exception as exc:
            logger.error("Erro cooldown %s: %s", symbol, exc)
            self.db_conn = None
            self.db_cursor = None
        return False

    async def fetch_data(self, symbol: str) -> pd.DataFrame | None:
        try:
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv, symbol, "15m", limit=MIN_CANDLES
            )
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            if len(df) < SEQ_LEN:
                logger.warning("%s: apenas %s candles (precisa %s)", symbol, len(df), SEQ_LEN)
                return None
            return df
        except Exception as exc:
            logger.error("Erro fetch %s: %s", symbol, exc)
            return None

    def compute_features(self, df: pd.DataFrame, symbol: str) -> np.ndarray:
        close = df["close"].values
        n = len(close)

        delta = np.diff(close, prepend=close[0])
        gain = np.maximum(delta, 0)
        loss = -np.minimum(delta, 0)
        avg_gain = pd.Series(gain).rolling(RSI_PERIOD).mean().values
        avg_loss = pd.Series(loss).rolling(RSI_PERIOD).mean().values
        rsi_14 = 100 - 100 / (1 + avg_gain / (avg_loss + 1e-10))
        rsi_smooth = pd.Series(rsi_14).ewm(span=2, adjust=False).mean().values
        rsi_4h = pd.Series(rsi_14).rolling(16).mean().values

        feats = np.column_stack([
            (rsi_14 - 50) / 10,
            (rsi_smooth - 50) / 10,
            (rsi_4h - 50) / 10,
        ])

        btc_feats = np.zeros((n, 5))
        try:
            btc_ohlcv = self.exchange.fetch_ohlcv("BTC/USDT", "1h", limit=60)
            if btc_ohlcv and len(btc_ohlcv) >= 50:
                btc_closes = np.array([c[4] for c in btc_ohlcv])
                btc_current = btc_closes[-1]
                btc_delta = np.diff(btc_closes, prepend=btc_closes[0])
                btc_g = np.maximum(btc_delta, 0)
                btc_l = -np.minimum(btc_delta, 0)
                btc_ag = pd.Series(btc_g).rolling(14).mean().values
                btc_al = pd.Series(btc_l).rolling(14).mean().values
                btc_rsi = 100 - 100 / (1 + btc_ag / (btc_al + 1e-10))
                btc_feats[:, 0] = (btc_rsi[-1] - 50) / 10
                for j, p in enumerate([12, 24, 36, 48]):
                    if len(btc_closes) >= p:
                        btc_feats[:, j + 1] = btc_current / max(btc_closes[-p:].mean(), 1)
        except Exception:
            pass
        feats = np.hstack([feats, btc_feats])

        extra = np.zeros((n, 4))
        try:
            fr_data = self._futures_ex.fetch_funding_rate_history(symbol, limit=2)
            if fr_data and len(fr_data) >= 2:
                fr = float(fr_data[-1].get("fundingRate", 0))
                fr_prev = float(fr_data[-2].get("fundingRate", 0))
                extra[:, 0] = fr * 10000
                extra[:, 1] = (fr - fr_prev) * 10000
            oi_data_1h = self.exchange.fetch_open_interest_history(symbol, "1h", limit=2)
            oi_data_24h = self.exchange.fetch_open_interest_history(symbol, "1h", limit=25)
            if oi_data_1h and len(oi_data_1h) >= 2:
                oi = float(oi_data_1h[-1].get("openInterestAmount", 0))
                oi_prev = float(oi_data_1h[-2].get("openInterestAmount", 0))
                extra[:, 2] = (oi / max(oi_prev, 1) - 1) * 100
            if oi_data_24h and len(oi_data_24h) >= 25:
                oi = float(oi_data_24h[-1].get("openInterestAmount", 0))
                oi_24h_ago = float(oi_data_24h[-25].get("openInterestAmount", 0))
                extra[:, 3] = (oi / max(oi_24h_ago, 1) - 1) * 100
        except Exception:
            pass
        feats = np.hstack([feats, extra])
        return np.nan_to_num(feats, nan=0.0)[-SEQ_LEN:]

    def predict(self, tier: str, features: np.ndarray) -> float:
        if tier not in self.models:
            return 0.5
        m = self.models[tier]
        nf = m.get("n_features", 3)
        seq_len = m["seq_len"]
        feats = features[-seq_len:, :nf]
        x = torch.from_numpy(feats).unsqueeze(0).float()
        with torch.no_grad():
            proba = m["model"](x).item()
        return round(proba, 4)

    def predict_short(self, tier: str, features: np.ndarray) -> float:
        if tier not in self.short_models:
            return 0.5
        m = self.short_models[tier]
        nf = m.get("n_features", 3)
        seq_len = m["seq_len"]
        feats = features[-seq_len:, :nf]
        x = torch.from_numpy(feats).unsqueeze(0).float()
        with torch.no_grad():
            proba = m["model"](x).item()
        return round(proba, 4)

    async def count_active_futures_positions(self) -> int:
        if not self.kv:
            return 0
        try:
            keys = await self.kv.keys()
            count = 0
            for key in keys:
                entry = await self.kv.get(key)
                if not entry:
                    continue
                val = json.loads(entry.value.decode())
                if val.get("is_futures") or val.get("venue") == "futures":
                    count += 1
            return count
        except Exception:
            return 0

    async def get_spot_usdt_balance(self) -> float:
        try:
            balance = await asyncio.to_thread(self.spot_exchange.fetch_balance)
            return float(balance["USDT"]["free"])
        except Exception as exc:
            logger.error("Erro balance Spot: %s", exc)
            return 0.0

    async def get_futures_usdt_balance(self) -> tuple[float, float]:
        try:
            balance = await asyncio.to_thread(self.futures_exchange.fetch_balance)
            usdt = balance.get("USDT", {})
            return float(usdt.get("total", 0.0)), float(usdt.get("free", 0.0))
        except Exception as exc:
            logger.error("Erro balance Futures: %s", exc)
            return 0.0, 0.0

    async def get_total_spot_portfolio(self) -> float:
        try:
            balance = await asyncio.to_thread(self.spot_exchange.fetch_balance)
            total = float(balance.get("USDT", {}).get("total", 0.0))
            for asset, amount in balance["total"].items():
                if asset == "USDT" or amount <= 0:
                    continue
                try:
                    ticker = await asyncio.to_thread(
                        self.spot_exchange.fetch_ticker, f"{asset}/USDT"
                    )
                    total += amount * ticker["last"]
                except Exception:
                    pass
            return total
        except Exception as exc:
            logger.error("Erro patrimônio Spot: %s", exc)
            return 0.0

    def _allowed_regimes(self, settings: dict, direction: str) -> list[str]:
        key = f"entry.{direction.lower()}_allowed_regimes"
        default = ["bull"] if direction.upper() == "LONG" else ["bear", "neutral"]
        regimes = settings.get(key, default)
        if isinstance(regimes, str):
            try:
                regimes = json.loads(regimes)
            except json.JSONDecodeError:
                regimes = [r.strip() for r in regimes.split(",") if r.strip()]
        return [str(r).lower() for r in regimes]

    def _resolve_route(
        self,
        settings: dict,
        direction: str,
        tier: str,
        score: float,
        futures_max_positions: int,
        active_futures: int,
        futures_balance: float,
        futures_free: float,
        leverage: int,
        min_notional: float,
    ) -> tuple[bool, int] | None:
        """Returns (is_futures, leverage), or None to skip the trade entirely."""
        is_short = direction.upper() == "SHORT"
        futures_enabled = get_bool(settings, "risk.futures_enabled", True)

        if is_short:
            is_futures = True
        else:
            is_futures = futures_enabled and score >= 0.70

        if not is_futures:
            return False, 1

        if active_futures >= futures_max_positions:
            if is_short:
                logger.warning(
                    "  Limite Futures atingido (%s/%s) — SHORT ignorado",
                    active_futures,
                    futures_max_positions,
                )
                return None
            logger.info("  Limite Futures — LONG desviado para Spot")
            return False, 1

        if leverage <= 1 and not is_short:
            logger.info("  LONG leverage 1x — rota Spot")
            return False, 1

        margin_required = max(min_notional, 6.0) / max(leverage, 1)
        if margin_required > futures_free * 0.98 or futures_free <= 1.0:
            if is_short:
                logger.warning("  SHORT sem margem Futures ($%.2f livre)", futures_free)
                return None
            logger.info("  Margem Futures insuficiente — LONG desviado para Spot")
            return False, 1

        return True, leverage

    async def _build_order(
        self,
        *,
        symbol: str,
        tier: str,
        strategy: str,
        direction: str,
        score: float,
        rsi_smooth: float,
        regime: str,
        df: pd.DataFrame,
        settings: dict,
        spot_balance: float,
        spot_portfolio: float,
        futures_balance: float,
        futures_free: float,
        active_futures: int,
        max_positions: int,
        futures_max_positions: int,
        timestamp: str,
    ) -> dict | None:
        is_short = direction.upper() == "SHORT"
        dir_lower = direction.lower()

        min_score = get_float(settings, entry_key(dir_lower, tier, "min_score"), 0.70)
        pct_2x = get_float(settings, entry_key(dir_lower, tier, "lev_2x_pct"), 0.20)
        pct_3x = get_float(settings, entry_key(dir_lower, tier, "lev_3x_pct"), 0.50)
        pct_5x = get_float(settings, entry_key(dir_lower, tier, "lev_5x_pct"), 0.80)
        leverage = calc_leverage(score, min_score, pct_2x, pct_3x, pct_5x)

        closes = df["close"].tolist()
        highs = df["high"].tolist()
        lows = df["low"].tolist()
        current_price = float(closes[-1])
        atr = compute_atr(highs, lows, closes, ATR_PERIOD)

        sl_pct = get_float(settings, entry_key(dir_lower, tier, "sl"), 3.0) / 100.0
        tp_pct = get_float(settings, entry_key(dir_lower, tier, "tp"), 3.0) / 100.0
        sl_price, tp_price = calc_sl_tp_prices(current_price, direction, sl_pct, tp_pct)

        min_notional = 6.0
        route = self._resolve_route(
            settings,
            direction,
            tier,
            score,
            futures_max_positions,
            active_futures,
            futures_balance,
            futures_free,
            leverage,
            min_notional,
        )
        if route is None:
            return None
        is_futures, leverage = route
        exchange = self.futures_exchange if is_futures else self.spot_exchange

        try:
            market_min = float(exchange.market(symbol)["limits"]["cost"]["min"])
            min_notional = max(market_min, 6.0)
        except Exception:
            pass

        if is_futures:
            candidate = (futures_balance * leverage) / max(futures_max_positions, 1)
            notional = max(candidate, min_notional)
        else:
            exposed = spot_portfolio * get_float(settings, "risk.risk_percent", 0.05)
            candidate = exposed / max(max_positions, 1)
            sl_min_qty = min_notional / sl_price if sl_price > 0 else 0
            sl_min_notional = sl_min_qty * current_price
            notional = max(candidate, min_notional, sl_min_notional)
            notional = min(notional, spot_balance * 0.98)
            leverage = 1

        quantity = notional / current_price if current_price > 0 else 0
        try:
            quantity = float(exchange.amount_to_precision(symbol, quantity))
        except Exception:
            pass

        final_notional = quantity * current_price
        if final_notional < min_notional:
            logger.info(
                "  %s %s: notional $%.2f < mínimo $%.2f",
                symbol,
                direction,
                final_notional,
                min_notional,
            )
            return None

        entry_type = str(settings.get("entry.default_type", "market")).strip('"').lower()
        if entry_type not in ("market", "limit"):
            entry_type = "market"

        signal = {
            "score": score,
            "rsi": round(rsi_smooth, 1),
            "strategy": strategy,
            "atr": round(atr, 6),
            "timestamp": timestamp,
        }
        if regime:
            signal["regime"] = regime

        client_order_id = build_client_order_id(BLOCK_ID, direction, tier, symbol)
        order = TradeOrder.build(
            block_id=BLOCK_ID,
            strategy=strategy,
            symbol=symbol,
            direction=direction,
            tier=tier,
            venue="futures" if is_futures else "spot",
            leverage=leverage,
            quantity=quantity,
            notional_usdt=round(final_notional, 2),
            sl_price=sl_price,
            tp_price=tp_price,
            client_order_id=client_order_id,
            entry_type=entry_type,
            entry_price=current_price if entry_type == "limit" else None,
            max_hold_hours=get_float(settings, "exit.max_hold_hours", 12),
            rsi_exit=get_float(settings, "exit.rsi_exit", 70),
            trailing_enabled=get_bool(settings, "exit.trailing_enabled", False),
            trailing_activation_atr=get_float(settings, "exit.trailing_activation_atr", 1.0),
            trailing_distance_atr=get_float(settings, "exit.trailing_distance_atr", 2.0),
            exit_mode=str(settings.get("exit.mode", "software")).strip('"'),
            signal=signal,
        )
        logger.info(
            "  [%s] %s %s qty=%s entry=%.6f SL=%.6f TP=%.6f lev=%sx $%.2f",
            "FUTURES" if is_futures else "SPOT",
            symbol,
            direction,
            quantity,
            current_price,
            sl_price,
            tp_price,
            leverage,
            final_notional,
        )
        return order

    async def process_universe(self, msg):
        try:
            data = json.loads(msg.data.decode())
            if isinstance(data, dict):
                assets = data.get("assets", [])
                regime = str(data.get("btc_trend", data.get("regime", "neutral"))).lower()
            else:
                assets = data
                regime = "neutral"

            settings = self.get_settings()
            cooldown_hours = get_float(settings, "risk.cooldown_hours", 2.0)
            max_positions = get_int(settings, "risk.max_positions", 20)
            futures_max_positions = get_int(settings, "risk.futures_max_positions", 3)

            logger.info("Processando %s ativos [regime=%s]", len(assets), regime)

            spot_balance = await self.get_spot_usdt_balance()
            futures_balance, futures_free = await self.get_futures_usdt_balance()
            spot_portfolio = await self.get_total_spot_portfolio()
            active_futures = await self.count_active_futures_positions()

            orders_published = 0

            for asset in assets:
                symbol = asset["symbol"]
                tier = asset.get("tier", "Major")
                timestamp = asset.get("timestamp", "")

                has_long = tier in self.models
                has_short = tier in self.short_models
                if not has_long and not has_short:
                    continue

                df = await self.fetch_data(symbol)
                if df is None or len(df) < SEQ_LEN:
                    continue

                features = self.compute_features(df, symbol)
                closes = df["close"].tolist()
                rsi_smooth, _ = compute_rsi_smooth(closes, RSI_PERIOD)
                if rsi_smooth is None:
                    continue

                long_score = self.predict(tier, features) if has_long else None
                short_score = self.predict_short(tier, features) if has_short else None
                logger.info(
                    "  %s (%s) long=%s short=%s RSI=%.1f",
                    symbol,
                    tier,
                    long_score,
                    short_score,
                    rsi_smooth,
                )

                candidates = []
                if long_score is not None:
                    candidates.append(
                        ("LONG", "mean_reversion_long", long_score, has_long)
                    )
                if short_score is not None:
                    candidates.append(
                        ("SHORT", "mean_reversion_short", short_score, has_short)
                    )

                for direction, strategy, score, _has_model in candidates:
                    dir_lower = direction.lower()

                    if not get_bool(settings, entry_allowed_key(direction, tier), True):
                        self.log_evaluation(
                            symbol, tier, strategy, direction, score, rsi_smooth,
                            regime, "REJECTED_TIER_DISABLED",
                        )
                        continue

                    allowed = self._allowed_regimes(settings, direction)
                    if regime not in allowed:
                        dec = "REJECTED_LATERAL" if regime == "neutral" else "REJECTED_REGIME"
                        self.log_evaluation(
                            symbol, tier, strategy, direction, score, rsi_smooth,
                            regime, dec,
                        )
                        continue

                    if self.is_in_cooldown(symbol, cooldown_hours):
                        self.log_evaluation(
                            symbol, tier, strategy, direction, score, rsi_smooth,
                            regime, "REJECTED_COOLDOWN",
                        )
                        continue

                    min_score = get_float(settings, entry_key(dir_lower, tier, "min_score"), 0.70)
                    if score < min_score:
                        self.log_evaluation(
                            symbol, tier, strategy, direction, score, rsi_smooth,
                            regime, "REJECTED_SCORE",
                        )
                        continue

                    if direction == "SHORT":
                        min_rsi = get_float(settings, entry_key("short", tier, "min_rsi"), 65.0)
                        if rsi_smooth < min_rsi:
                            self.log_evaluation(
                                symbol, tier, strategy, direction, score, rsi_smooth,
                                regime, "REJECTED_RSI",
                            )
                            continue
                    else:
                        max_rsi = get_float(settings, entry_key("long", tier, "max_rsi"), 38.0)
                        if rsi_smooth > max_rsi:
                            self.log_evaluation(
                                symbol, tier, strategy, direction, score, rsi_smooth,
                                regime, "REJECTED_RSI",
                            )
                            continue

                    order = await self._build_order(
                        symbol=symbol,
                        tier=tier,
                        strategy=strategy,
                        direction=direction,
                        score=score,
                        rsi_smooth=rsi_smooth,
                        regime=regime,
                        df=df,
                        settings=settings,
                        spot_balance=spot_balance,
                        spot_portfolio=spot_portfolio,
                        futures_balance=futures_balance,
                        futures_free=futures_free,
                        active_futures=active_futures,
                        max_positions=max_positions,
                        futures_max_positions=futures_max_positions,
                        timestamp=timestamp,
                    )
                    if order is None:
                        self.log_evaluation(
                            symbol, tier, strategy, direction, score, rsi_smooth,
                            regime, "REJECTED_SIZING",
                        )
                        continue

                    payload = json.dumps(order).encode()
                    await self.js.publish("trade.order", payload)
                    orders_published += 1
                    self.log_evaluation(
                        symbol, tier, strategy, direction, score, rsi_smooth,
                        regime, "ACCEPTED",
                    )

                    if order["venue"] == "futures":
                        active_futures += 1

            if orders_published:
                logger.info("Publicadas %s ordens em trade.order", orders_published)

            await msg.ack()
        except Exception as exc:
            logger.error("Erro ao processar leme.universe: %s", exc, exc_info=True)

    async def run(self):
        await self.connect_nats()
        await self.js.subscribe(
            "leme.universe",
            durable="LEME_ENGINE_WORKER",
            cb=self.process_universe,
            manual_ack=True,
            config=ConsumerConfig(ack_wait=120),
            pending_msgs_limit=512,
            pending_bytes_limit=64 * 1024 * 1024,
        )
        logger.info(
            "fb-leme-engine online — LONG: %s | SHORT: %s",
            list(self.models.keys()),
            list(self.short_models.keys()),
        )
        while True:
            if self.nc.is_closed:
                await self.connect_nats()
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(LemeEngine().run())
