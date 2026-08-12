import psycopg2, os

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

print("=" * 80)
print("TRADES FROM AUGUST 1 TO AUGUST 6 IN TRADE_LOG")
print("=" * 80)

cur.execute("""
    SELECT id, symbol, direction, tier, entry_price, exit_price, sl_price, tp_price, 
           quantity, leverage, is_futures, pnl_pct, exit_reason, score, rsi, market_regime, 
           created_at, updated_at, status
    FROM trade_log
    WHERE created_at >= '2026-08-01 00:00:00'
    ORDER BY id ASC
""")
cols = [desc[0] for desc in cur.description]
rows = cur.fetchall()

print(f"Total trades in August 2026: {len(rows)}")
for r in rows:
    t = dict(zip(cols, r))
    pnl = t['pnl_pct'] or 0.0
    res_str = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "EVEN")
    print(f"#{t['id']} [{t['status']}] {t['created_at']} | {t['direction']} {t['symbol']} ({t['tier']})")
    print(f"   Score: {t['score']} | RSI: {t['rsi']} | Regime: {t['market_regime']} | Lev: {t['leverage']}x ({'Futures' if t['is_futures'] else 'Spot'})")
    print(f"   Entry: {t['entry_price']} | Exit: {t['exit_price']} | SL: {t['sl_price']} | TP: {t['tp_price']}")
    print(f"   PnL%: {pnl:+.2f}% | Exit Reason: {t['exit_reason']} | Result: {res_str}")
    print("-" * 60)

conn.close()
