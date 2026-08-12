from __future__ import annotations

import psycopg2
from psycopg2.extensions import connection

from finbot_common.settings import load_block_settings, parse_setting_value


def connect(db_url: str) -> connection:
    return psycopg2.connect(db_url)


def fetch_block_settings(conn: connection, block_id: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT key, value FROM block_settings WHERE block_id = %s",
            (block_id,),
        )
        rows = cur.fetchall()
    return load_block_settings(rows)


def fetch_global_settings(conn: connection) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT key, value FROM global_settings")
        rows = cur.fetchall()
    settings = {}
    for key, value in rows:
        settings[key] = parse_setting_value(value)
    return settings


def upsert_block_setting(conn: connection, block_id: str, key: str, value) -> None:
    import json

    payload = json.dumps(value) if not isinstance(value, str) else value
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO block_settings (block_id, key, value, updated_at)
            VALUES (%s, %s, %s::jsonb, NOW())
            ON CONFLICT (block_id, key)
            DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """,
            (block_id, key, payload),
        )
    conn.commit()
