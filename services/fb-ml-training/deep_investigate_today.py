import psycopg2, os, json
from datetime import datetime

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

print("=== TODAY'S TRADES (LAST 48H) ===")
cur.execute("""
    SELECT id, symbol, direction, tier, entry_price, exit_price, quantity, leverage, 
           is_futures, pnl, pnl_pct, exit_reason, score, rsi, btc_trend, entry_time, exit_time, created_at
    FROM trade_log
    WHERE created_at >= NOW() - INTERVAL '48 hours'
    ORDER BY id DESC
""")
columns = [desc[0] for desc in cur.description]
rows = cur.fetchall()

today_trades = [dict(zip(columns, r)) for r in rows]
print(f"Total trades in last 48h: {len(today_trades)}")

for t in today_trades:
    print(f"[{t['id']}] {t['created_at']} | {t['direction']} {t['symbol']} ({t['tier']})")
    print(f"   Entry: {t['entry_price']} -> Exit: {t['exit_price']} | PnL: ${t['pnl']} ({t['pnl_pct']}%)")
    print(f"   Score: {t['score']} | RSI: {t['rsi']} | BTC Trend: {t['btc_trend']} | Exit Reason: {t['exit_reason']} | Lev: {t['leverage']}x (Futures={t['is_futures']})")
    print("-" * 60)

print("\n=== EVALUATIONS VS EXECUTIONS IN LAST 48H ===")
cur.execute("""
    SELECT COUNT(*), decision, rejection_reason
    FROM evaluations
    WHERE created_at >= NOW() - INTERVAL '48 hours'
    GROUP BY decision, rejection_reason
    ORDER BY COUNT(*) DESC
""")
eval_summary = cur.fetchall()
for row in eval_summary:
    print(f"   Count: {row[0]} | Decision: {row[1]} | Reason: {row[2]}")

conn.close()
