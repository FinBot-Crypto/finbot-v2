import os
import psycopg2
import pandas as pd

DB_URLS = [
    "postgresql://crypto_admin:ZNG5z43LaSrk7FEmwu6CPtRUB2IVKdvY@crypto-postgres:5432/crypto_bot",
    "postgresql://crypto_admin:ZNG5z43LaSrk7FEmwu6CPtRUB2IVKdvY@127.0.0.1:5432/crypto_bot",
    "postgresql://crypto_admin:ZNG5z43LaSrk7FEmwu6CPtRUB2IVKdvY@localhost:5432/crypto_bot"
]

def get_connection():
    for url in DB_URLS:
        try:
            conn = psycopg2.connect(url)
            return conn
        except:
            pass
    return None

def main():
    conn = get_connection()
    if not conn:
        print("Could not connect to database.")
        return

    # Check shadow_short_metrics by rsi_entry
    print("\n=== Shadow SHORT by rsi_entry ===")
    try:
        df_short = pd.read_sql("SELECT rsi_entry, pnl FROM shadow_short_metrics", conn)
        df_short['pnl'] = pd.to_numeric(df_short['pnl'], errors='coerce')
        df_short['rsi_entry'] = pd.to_numeric(df_short['rsi_entry'], errors='coerce')
        df_short = df_short.dropna(subset=['pnl', 'rsi_entry'])
        
        # Bucket rsi_entry
        bins = [0, 60, 65, 70, 75, 80, 85, 100]
        df_short['rsi_bucket'] = pd.cut(df_short['rsi_entry'], bins=bins)
        
        rsi_stats = df_short.groupby('rsi_bucket').agg(
            count=('pnl', 'count'),
            win_rate=('pnl', lambda x: (x > 0).mean() * 100),
            avg_pnl=('pnl', 'mean')
        ).reset_index()
        print(rsi_stats.to_string(index=False))
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()

    conn.close()

if __name__ == "__main__":
    main()
