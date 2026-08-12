import psycopg2, os

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

print("=" * 80)
print("EVALUATIONS LOG SUMMARY (LAST 48H)")
print("=" * 80)

cur.execute("""
    SELECT tier, direction, decision, COUNT(*), MIN(score), MAX(score), AVG(score), MIN(rsi), MAX(rsi)
    FROM evaluations_log
    WHERE created_at >= NOW() - INTERVAL '48 hours'
    GROUP BY tier, direction, decision
    ORDER BY tier, direction, decision
""")
for r in cur.fetchall():
    print(f"Tier: {r[0]} | Dir: {r[1]} | Decision: {r[2]} | Count: {r[3]} | Score range: [{r[4]:.4f} .. {r[5]:.4f}] (avg {r[6]:.4f}) | RSI range: [{r[7]:.1f} .. {r[8]:.1f}]")

print("\n" + "=" * 80)
print("RECENT ACCEPTED DECISIONS (LAST 7 DAYS)")
print("=" * 80)
cur.execute("""
    SELECT id, symbol, tier, direction, score, rsi, btc_trend, decision, created_at
    FROM evaluations_log
    WHERE decision LIKE 'ACCEPT%' OR decision LIKE 'BUY%' OR decision LIKE 'SELL%' OR decision = 'ACCEPTED'
    ORDER BY id DESC
    LIMIT 30
""")
accepted = cur.fetchall()
print(f"Total accepted evaluations in sample: {len(accepted)}")
for a in accepted:
    print(f"  #{a[0]} | {a[8]} | {a[1]} ({a[2]}) | Dir: {a[3]} | Decision: {a[7]} | Score: {a[4]} | RSI: {a[5]} | Trend: {a[6]}")

print("\n" + "=" * 80)
print("DISTINCT DECISIONS IN EVALUATIONS_LOG")
print("=" * 80)
cur.execute("SELECT decision, COUNT(*) FROM evaluations_log GROUP BY decision ORDER BY COUNT(*) DESC")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
