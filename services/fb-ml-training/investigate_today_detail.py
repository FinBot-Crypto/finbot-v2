import psycopg2, os, json

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

print("=" * 80)
print("TRADES CLOSED TODAY / RECENT (DETAILED)")
print("=" * 80)

cur.execute("""
    SELECT id, symbol, direction, tier, entry_price, exit_price, sl_price, tp_price, 
           quantity, leverage, is_futures, pnl_pct, exit_reason, score, rsi, market_regime, 
           created_at, updated_at
    FROM trade_log
    WHERE created_at >= '2026-07-27 00:00:00'
    ORDER BY id DESC
""")
cols = [desc[0] for desc in cur.description]
rows = cur.fetchall()

for r in rows:
    t = dict(zip(cols, r))
    entry = t['entry_price']
    exit_p = t['exit_price']
    sl = t['sl_price']
    tp = t['tp_price']
    direction = t['direction']
    pnl = t['pnl_pct']
    
    # Calculate price change
    if entry and exit_p:
        raw_change_pct = ((exit_p - entry) / entry) * 100 if direction == 'LONG' else ((entry - exit_p) / entry) * 100
    else:
        raw_change_pct = 0.0

    print(f"ID #{t['id']} | {t['created_at']} | {t['direction']} {t['symbol']} ({t['tier']})")
    print(f"   Score: {t['score']} | RSI: {t['rsi']} | Market Regime: {t['market_regime']}")
    print(f"   Lev: {t['leverage']}x (Futures={t['is_futures']}) | Qty: {t['quantity']}")
    print(f"   Entry Price: {entry} | SL Price: {sl} | TP Price: {tp} | Exit Price: {exit_p}")
    print(f"   PnL Pct: {pnl}% (Raw Price Change: {raw_change_pct:.2f}%) | Exit Reason: {t['exit_reason']}")
    print("-" * 70)

conn.close()
