import psycopg2, os

conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/finbot'))
cur = conn.cursor()

# Find all shadow tables
cur.execute("SELECT tablename FROM pg_tables WHERE tablename LIKE '%%shadow%%'")
print('All shadow tables:', cur.fetchall())

# Long scan by tier and trend
cur.execute('SELECT btc_trend, tier, COUNT(*) FROM shadow_long_scan GROUP BY btc_trend, tier ORDER BY tier, btc_trend')
print('\nshadow_long_scan by tier:')
for row in cur.fetchall():
    print(f'  {row}')

# Try shadow_short_metrics (the table the API uses)
try:
    cur.execute("SELECT btc_trend, tier, COUNT(*) FROM shadow_short_metrics GROUP BY btc_trend, tier ORDER BY tier, btc_trend")
    print('\nshadow_short_metrics by tier:')
    for row in cur.fetchall():
        print(f'  {row}')
except Exception as e:
    print(f'\nshadow_short_metrics error: {e}')
    conn.rollback()

# Try shadow_short_scan
try:
    cur.execute("SELECT btc_trend, tier, COUNT(*) FROM shadow_short_scan GROUP BY btc_trend, tier ORDER BY tier, btc_trend")
    print('\nshadow_short_scan by tier:')
    for row in cur.fetchall():
        print(f'  {row}')
except Exception as e:
    print(f'\nshadow_short_scan error: {e}')
    conn.rollback()

conn.close()
