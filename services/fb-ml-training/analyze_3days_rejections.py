import psycopg2, os

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

print("=" * 80)
print("ANALYSIS OF EVALUATIONS & REJECTIONS (AUG 3 08:00 -> AUG 6)")
print("=" * 80)

# Check total evaluations in Aug 3 - Aug 6
cur.execute("""
    SELECT decision, COUNT(*)
    FROM evaluations_log
    WHERE created_at >= '2026-08-03 08:00:00'
    GROUP BY decision
    ORDER BY COUNT(*) DESC
""")
rows = cur.fetchall()
total_evals = sum(x[1] for x in rows)
print(f"Total evaluations processed since Aug 3 08:00: {total_evals}")
print("Decisions breakdown:")
for r in rows:
    print(f"  {r[0]}: {r[1]} ({r[1] / total_evals * 100:.1f}%)")

print("\n" + "=" * 80)
print("REJECTIONS BREAKDOWN BY TIER & DIRECTION (AUG 3 -> AUG 6)")
print("=" * 80)

cur.execute("""
    SELECT tier, direction, decision, COUNT(*), 
           AVG(score), MIN(rsi), MAX(rsi)
    FROM evaluations_log
    WHERE created_at >= '2026-08-03 08:00:00'
    GROUP BY tier, direction, decision
    ORDER BY tier, direction, decision
""")
for r in cur.fetchall():
    tier, dirn, dec, count, avg_score, min_rsi, max_rsi = r
    min_rsi_str = f"{min_rsi:.1f}" if min_rsi is not None else "None"
    max_rsi_str = f"{max_rsi:.1f}" if max_rsi is not None else "None"
    avg_score_str = f"{avg_score:.3f}" if avg_score is not None else "None"
    print(f"  Tier: {tier:15s} | Dir: {dirn:5s} | Decision: {dec:22s} | Count: {count:6d} | Score avg: {avg_score_str} | RSI min/max: [{min_rsi_str} .. {max_rsi_str}]")

print("\n" + "=" * 80)
print("HIGH SCORE / POTENTIAL CANDIDATES THAT WERE REJECTED IN AUG 3 - AUG 6")
print("=" * 80)

print("\n1. LONG evaluations with Score >= 0.55 and RSI < 40:")
cur.execute("""
    SELECT symbol, tier, direction, score, rsi, btc_trend, decision, created_at
    FROM evaluations_log
    WHERE created_at >= '2026-08-03 08:00:00' AND direction = 'LONG' AND score >= 0.55 AND rsi < 40
    ORDER BY rsi ASC
    LIMIT 20
""")
long_cands = cur.fetchall()
if not long_cands:
    print("  None found with RSI < 40!")
for r in long_cands:
    rsi_str = f"{r[4]:.1f}" if r[4] is not None else "None"
    print(f"  {r[7]} | {r[0]} ({r[1]}) | Score: {r[3]} | RSI: {rsi_str} | Trend: {r[5]} | Decision: {r[6]}")

print("\n2. SHORT evaluations with Score >= 0.50 and RSI > 60:")
cur.execute("""
    SELECT symbol, tier, direction, score, rsi, btc_trend, decision, created_at
    FROM evaluations_log
    WHERE created_at >= '2026-08-03 08:00:00' AND direction = 'SHORT' AND score >= 0.50 AND rsi > 60
    ORDER BY rsi DESC
    LIMIT 20
""")
short_cands = cur.fetchall()
if not short_cands:
    print("  None found with RSI > 60!")
for r in short_cands:
    rsi_str = f"{r[4]:.1f}" if r[4] is not None else "None"
    print(f"  {r[7]} | {r[0]} ({r[1]}) | Score: {r[3]} | RSI: {rsi_str} | Trend: {r[5]} | Decision: {r[6]}")

conn.close()
