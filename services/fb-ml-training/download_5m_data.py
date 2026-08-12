"""
Script para baixar histórico de 5m de todos os ativos configurados e salvar em data/raw/.
Usa Binance como primário e Gate.io como fallback (caso esteja em local restrito/EUA).
"""
import os
import sys
import asyncio
import pandas as pd
import ccxt
from src.shared.config import TIER_SYMBOLS

# Adiciona o diretório atual ao path
sys.path.insert(0, os.getcwd())

async def download_symbol(symbol: str, exchange_name: str, limit: int = 12000) -> pd.DataFrame:
    print(f"Baixando {symbol} de {exchange_name}...")
    
    # Inicializa exchange
    if exchange_name == 'binance':
        exch = ccxt.binance({'enableRateLimit': True})
    else:
        exch = ccxt.gateio({'enableRateLimit': True})
        
    all_candles = []
    timeframe = '5m'
    max_per_request = 1000
    
    try:
        # Verifica se o par existe na exchange
        markets = await asyncio.to_thread(exch.load_markets)
        if symbol not in markets:
            print(f"  Par {symbol} não encontrado em {exchange_name}")
            return None
            
        since = None
        # Pega chunks de 1000 velas retroativamente até atingir o limite
        while len(all_candles) < limit:
            params = {}
            if all_candles:
                # endTime ou since dependendo da exchange
                # Para simplificar e evitar paginação complexa em diferentes exchanges,
                # usamos 'since' calculado com base no timestamp da primeira vela do buffer
                first_ts = all_candles[0][0]
                # Subtrai max_per_request * 5 minutos em ms
                since = first_ts - (max_per_request * 5 * 60 * 1000)
            
            chunk = await asyncio.to_thread(
                exch.fetch_ohlcv, symbol, timeframe, since, max_per_request, params
            )
            
            if not chunk:
                break
                
            # Adiciona ao início do buffer
            # Evita duplicados
            if all_candles:
                existing_timestamps = {c[0] for c in all_candles}
                chunk = [c for c in chunk if c[0] not in existing_timestamps]
            
            if not chunk:
                break
                
            all_candles = chunk + all_candles
            # Se vier menos que o esperado, significa que atingimos o limite do histórico da exchange
            if len(chunk) < max_per_request:
                break
                
            # Pequeno sleep para evitar rate limit
            await asyncio.sleep(0.1)
            
        if not all_candles:
            return None
            
        all_candles = all_candles[-limit:]
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
        
    except Exception as e:
        print(f"  Falha no download de {symbol} via {exchange_name}: {e}")
        return None

async def main():
    dest_dir = os.path.join('data', 'raw')
    os.makedirs(dest_dir, exist_ok=True)
    
    # Junta todos os símbolos
    all_symbols = []
    for tier, symbols in TIER_SYMBOLS.items():
        all_symbols.extend(symbols)
        
    # Remove duplicatas mantendo a ordem
    unique_symbols = list(dict.fromkeys(all_symbols))
    
    print(f"Total de símbolos para baixar: {len(unique_symbols)}")
    
    for symbol in unique_symbols:
        name = symbol.replace('/', '_')
        csv_path = os.path.join(dest_dir, f"{name}_5m.csv")
        
        # Tenta primeiro Binance
        df = await download_symbol(symbol, 'binance')
        
        # Se falhar, tenta Gate.io
        if df is None:
            print(f"  Tentando fallback para Gate.io...")
            df = await download_symbol(symbol, 'gateio')
            
        if df is not None and len(df) > 0:
            df.to_csv(csv_path, index=False)
            print(f"  SUCESSO: {symbol} salvo em {csv_path} ({len(df)} velas)")
        else:
            print(f"  ERRO: Não foi possível obter dados para {symbol}")

if __name__ == "__main__":
    asyncio.run(main())
