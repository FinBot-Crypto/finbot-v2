"""
fb-leme-guardian: pausa/reactiva direction+tier via block_settings.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import nats
import psycopg2
from finbot_common.db import fetch_block_settings, upsert_block_setting
from finbot_common.settings import entry_allowed_key, get_bool, get_float, get_int
from nats.js.api import ConsumerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fb-leme-guardian")

NATS_URL = os.getenv("NATS_URL", "nats://crypto-nats:4222")
DATABASE_URL = os.getenv("DATABASE_URL", "")
BLOCK_ID = "leme"

TIERS = ["Major", "Strong Alt", "High Volatility"]
DIRECTIONS = ["long", "short"]


class LemeGuardian:
    def __init__(self):
        self.nc = None
        self.js = None

    async def connect_nats(self):
        self.nc = await nats.connect(NATS_URL)
        self.js = self.nc.jetstream()

    def _tier_key(self, tier: str) -> str:
        return tier.lower().replace(" ", "_")

    def _scope(self, direction: str, tier: str) -> str:
        return f"{direction}_{tier}"

    def apply_disable(self, conn, direction: str, tier: str, reason: str):
        key = entry_allowed_key(direction, tier)
        upsert_block_setting(conn, BLOCK_ID, key, False)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO guardian_events (block_id, action, reason, scope)
                VALUES (%s, 'DISABLE', %s, %s)
                """,
                (BLOCK_ID, reason, self._scope(direction, tier)),
            )
        conn.commit()
        logger.warning("LEME DISABLE %s/%s: %s", direction, tier, reason)

    def apply_enable(self, conn, direction: str, tier: str, reason: str):
        key = entry_allowed_key(direction, tier)
        upsert_block_setting(conn, BLOCK_ID, key, True)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO guardian_events (block_id, action, reason, scope)
                VALUES (%s, 'ENABLE', %s, %s)
                """,
                (BLOCK_ID, reason, self._scope(direction, tier)),
            )
        conn.commit()
        logger.info("LEME ENABLE %s/%s: %s", direction, tier, reason)

    async def evaluate(self):
        if not DATABASE_URL:
            return
        conn = psycopg2.connect(DATABASE_URL)
        settings = fetch_block_settings(conn, BLOCK_ID)

        max_sl = get_int(settings, "guardian.max_consecutive_sl", 3)
        min_wr = get_float(settings, "guardian.min_win_rate", 40)
        cooldown_h = get_float(settings, "guardian.cooldown_hours", 24)
        shadow_min = get_int(settings, "guardian.shadow_min_trades", 5)
        shadow_wr = get_float(settings, "guardian.shadow_min_winrate", 60)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (symbol) symbol, tier
                FROM evaluations_log
                WHERE block_id = %s AND tier IS NOT NULL
                ORDER BY symbol, created_at DESC
                """,
                (BLOCK_ID,),
            )
            symbol_tiers = {r[0]: r[1] for r in cur.fetchall()}

        for direction in DIRECTIONS:
            for tier in TIERS:
                allowed_key = entry_allowed_key(direction, tier)
                is_allowed = get_bool(settings, allowed_key, True)
                tier_symbols = [s for s, t in symbol_tiers.items() if t == tier]
                if not tier_symbols:
                    continue

                sym_filter = "symbol = %s" if len(tier_symbols) == 1 else "symbol = ANY(%s)"
                sym_param = tier_symbols[0] if len(tier_symbols) == 1 else tier_symbols

                with conn.cursor() as cur:
                    if is_allowed:
                        cur.execute(
                            f"""
                            SELECT pnl_pct FROM positions
                            WHERE block_id = %s AND status = 'CLOSED'
                              AND direction = %s AND {sym_filter}
                            ORDER BY closed_at DESC LIMIT %s
                            """,
                            (BLOCK_ID, direction.upper(), sym_param, max_sl),
                        )
                        recent = cur.fetchall()
                        if len(recent) >= max_sl and all(r[0] is not None and float(r[0]) < 0 for r in recent):
                            self.apply_disable(
                                conn,
                                direction,
                                tier,
                                f"{max_sl} SL consecutivos em trades reais",
                            )
                            continue

                        cur.execute(
                            f"""
                            SELECT pnl_pct FROM positions
                            WHERE block_id = %s AND status = 'CLOSED'
                              AND direction = %s AND {sym_filter}
                            ORDER BY closed_at DESC LIMIT 10
                            """,
                            (BLOCK_ID, direction.upper(), sym_param),
                        )
                        last10 = cur.fetchall()
                        if len(last10) >= 5:
                            wins = sum(1 for r in last10 if r[0] is not None and float(r[0]) > 0)
                            wr = wins / len(last10) * 100
                            if wr < min_wr:
                                self.apply_disable(
                                    conn,
                                    direction,
                                    tier,
                                    f"Win-rate {wr:.1f}% abaixo de {min_wr}%",
                                )
                    else:
                        cur.execute(
                            """
                            SELECT created_at FROM guardian_events
                            WHERE block_id = %s AND scope = %s AND action = 'DISABLE'
                            ORDER BY created_at DESC LIMIT 1
                            """,
                            (BLOCK_ID, self._scope(direction, tier)),
                        )
                        last = cur.fetchone()
                        if last:
                            elapsed = (datetime.now(timezone.utc) - last[0].replace(tzinfo=timezone.utc)).total_seconds() / 3600
                            if elapsed < cooldown_h:
                                continue

                        table = "leme_shadow_long" if direction == "long" else "leme_shadow_short"
                        cur.execute(
                            f"""
                            SELECT pnl FROM {table}
                            WHERE tier = %s AND sl = 3.0 AND tp = 3.0
                            ORDER BY entry_ts DESC LIMIT %s
                            """,
                            (tier, shadow_min),
                        )
                        shadow = cur.fetchall()
                        if len(shadow) >= shadow_min:
                            wins = sum(1 for r in shadow if r[0] > 0)
                            wr = wins / len(shadow) * 100
                            if wr >= shadow_wr:
                                self.apply_enable(
                                    conn,
                                    direction,
                                    tier,
                                    f"Shadow recovery {wr:.1f}% nos últimos {len(shadow)}",
                                )

        conn.close()

    async def on_trade_closed(self, msg):
        try:
            await self.evaluate()
            await msg.ack()
        except Exception as exc:
            logger.error("trade.closed handler: %s", exc)

    async def loop(self):
        while True:
            try:
                await self.evaluate()
            except Exception as exc:
                logger.error("guardian loop: %s", exc)
            await asyncio.sleep(600)

    async def run(self):
        await self.connect_nats()
        await self.evaluate()
        await self.js.subscribe(
            "trade.closed",
            durable="LEME_GUARDIAN",
            cb=self.on_trade_closed,
            manual_ack=True,
            config=ConsumerConfig(ack_wait=30),
        )
        asyncio.create_task(self.loop())
        logger.info("fb-leme-guardian online")
        while True:
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(LemeGuardian().run())
