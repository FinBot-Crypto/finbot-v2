import psycopg2, os, json
from datetime import datetime

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

print("=" * 80)
print("1. RECENT TRADES IN TRADE_LOG (LAST 10 DAYS)")
print("=" * 80)
cur.execute("""
    SELECT id, symbol, direction, tier, entry_price, exit_price, sl_price, tp_price, 
           quantity, leverage, is_futures, pnl_pct, exit_reason, score, rsi, market_regime, 
           created_at, updated_at
    FROM trade_log
    ORDER BY id DESC
    LIMIT 50
""")
columns = [desc[0] for desc in cur.description]
rows = cur.fetchall()

trades = [dict(zip(columns, r)) for r in rows]

print(f"Total retrieved: {len(trades)}")
for t in trades:
    print(f"ID #{t['id']} | {t['created_at']} -> {t['updated_at']}")
    print(f"   {t['direction']} {t['symbol']} | Tier: {t['tier']} | Regime: {t['market_regime']}")
    print(f"   Score: {t['score']} | RSI: {t['rsi']} | Lev: {t['leverage']}x (Futures={t['is_futures']})")
    print(f"   Entry: {t['entry_price']} | SL: {t['sl_price']} | TP: {t['tp_price']} | Exit: {t['exit_price']}")
    print(f"   PnL%: {t['pnl_pct']}% | Exit Reason: {t['exit_reason']}")
    print("-" * 60)

print("\n" + "=" * 80)
print("2. BOT SETTINGS IN DB (CURRENTLY IN EFFECT)")
print("=" * 80)
cur.execute("SELECT key, value, updated_at FROM bot_settings ORDER BY key")
settings = cur.fetchall()
for s in settings:
    print(f"{s[0]} = {s[1]} (updated: {s[2]})")

print("\n" + "=" * 80)
print("3. CHECKING LEME / PAUSE DECISIONS HISTORY")
print("=" * 80)
try:
    cur.execute("SELECT * FROM leme_decisions ORDER BY id DESC LIMIT 20")
    cols = [desc[0] for desc in cur.description]
    for r in cur.fetchall():
        print(dict(zip(cols, r)))
except Exception as e:
    print("leme_decisions error or table missing:", e)
    conn.rollback()

try:
    cur.execute("SELECT * FROM leme_events ORDER BY id DESC LIMIT 20")
    cols = [desc[0] for desc in cur.description]
    for r in cur.fetchall():
        print(dict(zip(cols, r)))
except Exception as e:
    print("leme_events error or table missing:", e)
    conn.rollback()

conn.close()
