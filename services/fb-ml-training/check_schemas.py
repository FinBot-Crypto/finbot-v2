import psycopg2, os, json

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'trade_log'")
print("trade_log columns:", cur.fetchall())

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'evaluations'")
print("evaluations columns:", cur.fetchall())

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'bot_settings'")
print("bot_settings columns:", cur.fetchall())

conn.close()
