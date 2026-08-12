import psycopg2, os

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

cur.execute("SELECT MAX(created_at), COUNT(*) FROM evaluations_log")
r = cur.fetchone()
print(f"Latest record in evaluations_log: {r[0]} | Total rows: {r[1]}")

cur.execute("SELECT MAX(created_at), COUNT(*) FROM trade_log")
r = cur.fetchone()
print(f"Latest record in trade_log: {r[0]} | Total rows: {r[1]}")

cur.execute("SELECT MAX(created_at), COUNT(*) FROM leme_decisions")
r = cur.fetchone()
print(f"Latest record in leme_decisions: {r[0]} | Total rows: {r[1]}")

conn.close()
