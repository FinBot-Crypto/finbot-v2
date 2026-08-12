import psycopg2, os, json
from datetime import datetime

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

print("=" * 80)
print("1. SUMMARY OF TRADES SINCE LAST DEPLOY (JULY 28 -> AUG 6)")
print("=" * 80)
cur.execute("""
    SELECT id, symbol, direction, tier, entry_price, exit_price, sl_price, tp_price, 
           quantity, leverage, is_futures, pnl_pct, exit_reason, score, rsi, market_regime, 
           created_at, updated_at, status
    FROM trade_log
    WHERE created_at >= '2026-07-28 00:00:00'
    ORDER BY id DESC
""")
cols = [desc[0] for desc in cur.description]
rows = cur.fetchall()

trades = [dict(zip(cols, r)) for r in rows]
print(f"Total trades since July 28: {len(trades)}")

closed_trades = [t for t in trades if t['status'] == 'CLOSED']
open_trades = [t for t in trades if t['status'] == 'OPEN']

print(f"  OPEN trades: {len(open_trades)}")
print(f"  CLOSED trades: {len(closed_trades)}")

if closed_trades:
    wins = sum(1 for t in closed_trades if (t['pnl_pct'] or 0) > 0)
    losses = sum(1 for t in closed_trades if (t['pnl_pct'] or 0) <= 0)
    total_pnl = sum(t['pnl_pct'] or 0 for t in closed_trades)
    wr = (wins / len(closed_trades)) * 100 if closed_trades else 0
    print(f"  Stats: {wins} Wins / {losses} Losses | Win Rate: {wr:.1f}% | Total PnL: {total_pnl:+.2f}%")

print("\n--- ALL RECENT TRADES ---")
for t in trades:
    pnl = t['pnl_pct'] or 0.0
    res_str = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "EVEN")
    print(f"#{t['id']} [{t['status']}] {t['created_at']} | {t['direction']} {t['symbol']} ({t['tier']})")
    print(f"   Score: {t['score']} | RSI: {t['rsi']} | Regime: {t['market_regime']} | Lev: {t['leverage']}x ({'Futures' if t['is_futures'] else 'Spot'})")
    print(f"   Entry: {t['entry_price']} | Exit: {t['exit_price']} | SL: {t['sl_price']} | TP: {t['tp_price']}")
    print(f"   PnL%: {pnl:+.2f}% | Exit Reason: {t['exit_reason']} | Result: {res_str}")
    print("-" * 60)

print("\n" + "=" * 80)
print("2. BOT SETTINGS CURRENTLY IN DB")
print("=" * 80)
cur.execute("SELECT key, value, updated_at FROM bot_settings ORDER BY key")
settings = cur.fetchall()
for s in settings:
    print(f"  {s[0]} = {s[1]} (updated: {s[2]})")

print("\n" + "=" * 80)
print("3. LEME DECISIONS HISTORY (RECENT)")
print("=" * 80)
try:
    cur.execute("SELECT id, group_name, action, reason, created_at FROM leme_decisions ORDER BY id DESC LIMIT 15")
    for r in cur.fetchall():
        print(f"  #{r[0]} | {r[4]} | {r[1]} -> {r[2]} | Reason: {r[3]}")
except Exception as e:
    print("  Error reading leme_decisions:", e)
    conn.rollback()

print("\n" + "=" * 80)
print("4. EVALUATIONS / REJECTION REASONS IN LAST 48 HOURS BY TIER")
print("=" * 80)
try:
    cur.execute("""
        SELECT tier, strategy, direction, decision, rejection_reason, COUNT(*)
        FROM evaluations_log
        WHERE created_at >= NOW() - INTERVAL '48 hours'
        GROUP BY tier, strategy, direction, decision, rejection_reason
        ORDER BY tier, decision, COUNT(*) DESC
    """)
    for r in cur.fetchall():
        print(f"  Tier: {r[0]} | Strategy: {r[1]} | Dir: {r[2]} | Decision: {r[3]} | Count: {r[5]} | Reason: {r[4]}")
except Exception as e:
    print("  evaluations_log query error (checking evaluations instead):", e)
    conn.rollback()
    try:
        cur.execute("""
            SELECT decision, rejection_reason, COUNT(*)
            FROM evaluations
            WHERE created_at >= NOW() - INTERVAL '48 hours'
            GROUP BY decision, rejection_reason
            ORDER BY COUNT(*) DESC
        """)
        for r in cur.fetchall():
            print(f"  Decision: {r[0]} | Count: {r[2]} | Reason: {r[1]}")
    except Exception as e2:
        print("  evaluations query error:", e2)

conn.close()
