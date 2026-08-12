import psycopg2, os

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

print("=" * 80)
print("REJECTION REASONS IN LAST 24 HOURS BY TIER & DIRECTION")
print("=" * 80)

cur.execute("""
    SELECT tier, direction, decision, COUNT(*), MIN(score), MAX(score), AVG(score), MIN(rsi), MAX(rsi)
    FROM evaluations_log
    WHERE created_at >= NOW() - INTERVAL '24 hours'
    GROUP BY tier, direction, decision
    ORDER BY tier, direction, decision
""")
for r in cur.fetchall():
    print(f"Tier: {r[0]} | Dir: {r[1]} | Decision: {r[2]} | Count: {r[3]} | Scores: [{r[4]:.3f}..{r[5]:.3f}] (avg {r[6]:.3f}) | RSI: [{r[7]:.1f}..{r[8]:.1f}]")

print("\n" + "=" * 80)
print("HIGHEST SCORE / EXTREME RSI OPPORTUNITIES IN LAST 24 HOURS")
print("=" * 80)
print("\nTop 10 LONG candidate evaluations (lowest RSI):")
cur.execute("""
    SELECT symbol, tier, direction, score, rsi, btc_trend, decision, created_at
    FROM evaluations_log
    WHERE created_at >= NOW() - INTERVAL '24 hours' AND direction = 'LONG'
    ORDER BY rsi ASC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[7]} | {r[0]} ({r[1]}) | Score: {r[3]} | RSI: {r[4]:.1f} | Trend: {r[5]} | Decision: {r[6]}")

print("\nTop 10 SHORT candidate evaluations (highest RSI):")
cur.execute("""
    SELECT symbol, tier, direction, score, rsi, btc_trend, decision, created_at
    FROM evaluations_log
    WHERE created_at >= NOW() - INTERVAL '24 hours' AND direction = 'SHORT'
    ORDER BY rsi DESC
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"  {r[7]} | {r[0]} ({r[1]}) | Score: {r[3]} | RSI: {r[4]:.1f} | Trend: {r[5]} | Decision: {r[6]}")

conn.close()
