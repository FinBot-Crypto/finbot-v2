import psycopg2, os

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name LIKE '%eval%'")
print("Evaluation tables & columns:")
for r in cur.fetchall():
    print(r)

cur.execute("SELECT tablename FROM pg_tables WHERE tablename LIKE '%eval%' OR tablename LIKE '%log%'")
print("\nTables:", cur.fetchall())

conn.close()
