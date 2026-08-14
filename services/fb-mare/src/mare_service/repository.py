from __future__ import annotations

import json
from typing import Any

import psycopg2


class Repository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def connect(self):
        if not self.database_url:
            return None
        return psycopg2.connect(self.database_url)

    def settings(self) -> dict[str, Any]:
        conn = self.connect()
        if conn is None:
            return {}
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT key, value FROM block_settings WHERE block_id='mare'")
                result = {}
                for key, value in cur.fetchall():
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                    result[key] = value
                return result
        finally:
            conn.close()

    def block_enabled(self) -> bool:
        conn = self.connect()
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT enabled FROM strategy_blocks WHERE id='mare'")
                row = cur.fetchone()
                return bool(row and row[0])
        finally:
            conn.close()

    def save_signal(self, signal: dict, block_enabled: bool, live_orders_enabled: bool) -> None:
        conn = self.connect()
        if conn is None:
            return
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mare_signals
                        (symbol, direction, score, accepted, reason, tide_state, wave_state,
                         ripple_state, price, atr, block_enabled, live_orders_enabled, payload)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    """,
                    (
                        signal["symbol"], signal.get("direction"), signal["score"], signal["accepted"], signal["reason"],
                        signal["tide"]["state"], signal["wave"]["state"], signal["ripple"]["state"],
                        signal["price"], signal["atr"], block_enabled, live_orders_enabled, json.dumps(signal),
                    ),
                )
            conn.commit()
        finally:
            conn.close()
