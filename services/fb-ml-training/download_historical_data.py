"""
Script de download unificado de dados históricos para o robô de ML.
Baixa timeframes: 5m, 15m, 1h para todos os 19 símbolos configurados.
Baixa também taxas de funding e open interest históricos.
Usa Binance como primário e Gate.io como fallback (se necessário).
"""
import os
import sys
import time
import pandas as pd
import ccxt

# Adiciona o diretório atual ao path para importações locais
sys.path.insert(0, os.getcwd())
from src.shared.config import TIER_SYMBOLS

# Configurações de limites de velas por timeframe
TIMEFRAME_LIMITS = {
    '5m': 100000,   # ~1 ano de dados
    '15m': 80000,   # ~2.3 anos de dados
    '1h': 30000     # ~3.4 anos de dados
}

def download_ohlcv(symbol: str, timeframe: str, limit: int, exchange_name: str) -> pd.DataFrame:
    print(f"  Acessando {symbol} em {exchange_name}...")
    
    if exchange_name == 'binance':
        exch = ccxt.binance({'enableRateLimit': True})
    else:
        exch = ccxt.gateio({'enableRateLimit': True})
        
    all_candles = []
    max_per_request = 1000
    
    try:
        exch.load_markets()
        if symbol not in exch.markets:
            print(f"    Par {symbol} não disponível na {exchange_name}")
            return None
            
        tf_ms = exch.parse_timeframe(timeframe) * 1000
        since = None
        
        while len(all_candles) < limit:
            if all_candles:
                # Pega o timestamp do candle mais antigo no buffer e solicita dados anteriores a ele
                since = all_candles[0][0] - (max_per_request * tf_ms)
                
            chunk = exch.fetch_ohlcv(symbol, timeframe, since, max_per_request)
            if not chunk:
                break
                
            # Evita duplicatas de timestamp
            if all_candles:
                existing_ts = {c[0] for c in all_candles}
                chunk = [c for c in chunk if c[0] not in existing_ts]
                
            if not chunk:
                break
                
            all_candles = chunk + all_candles
            if len(chunk) < max_per_request:
                # Atingiu o limite de histórico disponível na exchange
                break
                
            time.sleep(0.1) # Rate limit protection
            
        if not all_candles:
            return None
            
        all_candles = all_candles[-limit:]
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
        
    except Exception as e:
        print(f"    Falha ao baixar {symbol} ({timeframe}) de {exchange_name}: {e}")
        return None

def download_funding(symbol: str) -> pd.DataFrame:
    try:
        exch = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
        exch.load_markets()
        if symbol not in exch.markets:
            return None
        data = exch.fetch_funding_rate_history(symbol, limit=1000)
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[['timestamp', 'fundingRate']].drop_duplicates('timestamp')
            return df
    except Exception as e:
        print(f"    Falha ao baixar funding de {symbol}: {e}")
    return None

def download_oi(symbol: str) -> pd.DataFrame:
    try:
        exch = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
        exch.load_markets()
        if symbol not in exch.markets:
            return None
        data = exch.fetch_open_interest_history(symbol, '1h', limit=1000)
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[['timestamp', 'openInterestValue']].drop_duplicates('timestamp')
            return df
    except Exception as e:
        print(f"    Falha ao baixar open interest de {symbol}: {e}")
    return None

def main():
    dest_dir = os.path.join('data', 'raw')
    
    # 1. Obter todos os símbolos configurados
    all_symbols = []
    for tier, symbols in TIER_SYMBOLS.items():
        all_symbols.extend(symbols)
    unique_symbols = list(dict.fromkeys(all_symbols))
    
    print(f"Iniciando download histórico para {len(unique_symbols)} símbolos...")
    
    # 2. Loop por timeframe e download dos dados OHLCV
    for tf, limit in TIMEFRAME_LIMITS.items():
        tf_dir = os.path.join(dest_dir, tf)
        os.makedirs(tf_dir, exist_ok=True)
        print(f"\n=== TIMEFRAME {tf} (Limite: {limit} velas) ===")
        
        for symbol in unique_symbols:
            name = symbol.replace('/', '_')
            csv_path = os.path.join(tf_dir, f"{name}.csv")
            
            # Pula se já tiver dados suficientes (evita re-download desnecessário localmente)
            if os.path.exists(csv_path):
                existing_df = pd.read_csv(csv_path)
                if len(existing_df) >= limit * 0.95: # tolerância de 5%
                    print(f"  {symbol} ({tf}) já existe localmente com {len(existing_df)} velas. Pulando.")
                    continue
            
            # Tenta Binance
            df = download_ohlcv(symbol, tf, limit, 'binance')
            
            # Fallback para Gate.io se falhar/bloquear
            if df is None:
                print(f"    Tentando fallback para Gate.io...")
                df = download_ohlcv(symbol, tf, limit, 'gateio')
                
            if df is not None and len(df) > 0:
                df.to_csv(csv_path, index=False)
                print(f"    -> Salvo em {csv_path} ({len(df)} velas)")
            else:
                print(f"    -> ERRO: Não foi possível obter dados para {symbol} ({tf})")
            
            time.sleep(0.5) # Proteção rate limit geral

    # 3. Download dos dados de Futuros (Funding Rate + Open Interest)
    futures_dir = os.path.join(dest_dir, 'futures')
    os.makedirs(futures_dir, exist_ok=True)
    print("\n=== DADOS DE FUTUROS (Funding Rate + Open Interest) ===")
    
    for symbol in unique_symbols:
        name = symbol.replace('/', '_')
        
        # Funding Rate
        funding_path = os.path.join(futures_dir, f"{name}_funding.csv")
        df_funding = download_funding(symbol)
        if df_funding is not None and len(df_funding) > 0:
            df_funding.to_csv(funding_path, index=False)
            print(f"  Funding {symbol} salvo ({len(df_funding)} registros)")
            
        # Open Interest
        oi_path = os.path.join(futures_dir, f"{name}_oi.csv")
        df_oi = download_oi(symbol)
        if df_oi is not None and len(df_oi) > 0:
            df_oi.to_csv(oi_path, index=False)
            print(f"  Open Interest {symbol} salvo ({len(df_oi)} registros)")
            
        time.sleep(0.5)

    print("\nTodo o download de dados históricos foi concluído com sucesso!")

if __name__ == "__main__":
    main()
