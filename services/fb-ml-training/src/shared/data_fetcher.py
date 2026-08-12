"""
Fetcher de dados OHLCV com fallback:
1. Binance (API)
2. Kraken (API - funciona de qualquer lugar)
3. CSV local (data/raw/)
"""
import logging
import asyncio
import os
import pandas as pd
import ccxt
from typing import Optional, List

logger = logging.getLogger(__name__)

SYMBOL_MAP = {'BTC/USDT': 'BTC/USDT', 'ETH/USDT': 'ETH/USDT'}
MAX_PER_REQUEST = 1000

# Tenta encontrar o diretorio raiz do projeto
_ROOTS = [
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '/content/fb-ml-training',
    '/app',
    os.getcwd(),
]


class DataFetcher:
    """
    Fetcher OHLCV + Funding Rate + Open Interest da Binance.
    """

    def __init__(self):
        self.exchanges = []
        self.futures_ex = None
        self._init_exchange('binance')
        try:
            self.futures_ex = ccxt.binance({'options': {'defaultType': 'future'}, 'enableRateLimit': True})
        except:
            pass
        logger.info("DataFetcher: binance api + csv fallback")

    async def fetch_funding_rate_history(self, symbol: str, limit: int = 1000) -> pd.DataFrame:
        """Funding rate com CSV como padrão e API como fallback."""
        # 1. Tenta carregar do CSV local (padrão)
        name = symbol.replace('/', '_')
        for root in _ROOTS:
            p = os.path.join(root, 'data', 'raw', 'futures', f'{name}_funding.csv')
            if os.path.exists(p):
                df = pd.read_csv(p, parse_dates=['timestamp'])
                logger.info(f"OK {symbol} funding (CSV local): {len(df)} registros")
                return df.set_index('timestamp')

        # 2. Fallback para API da Binance
        if self.futures_ex:
            try:
                data = await asyncio.to_thread(self.futures_ex.fetch_funding_rate_history, symbol, limit=limit)
                if data:
                    df = pd.DataFrame(data)
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    return df[['timestamp', 'fundingRate']].drop_duplicates('timestamp').set_index('timestamp')
            except:
                pass
        return pd.DataFrame()

    async def fetch_open_interest_history(self, symbol: str, limit: int = 1000) -> pd.DataFrame:
        """Open interest com CSV como padrão e API como fallback."""
        # 1. Tenta carregar do CSV local (padrão)
        name = symbol.replace('/', '_')
        for root in _ROOTS:
            p = os.path.join(root, 'data', 'raw', 'futures', f'{name}_oi.csv')
            if os.path.exists(p):
                df = pd.read_csv(p, parse_dates=['timestamp'])
                logger.info(f"OK {symbol} open interest (CSV local): {len(df)} registros")
                return df.set_index('timestamp')

        # 2. Fallback para API da Binance
        if self.futures_ex:
            try:
                data = await asyncio.to_thread(self.futures_ex.fetch_open_interest_history, symbol, '1h', limit=limit)
                if data:
                    df = pd.DataFrame(data)
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    return df[['timestamp', 'openInterestValue']].drop_duplicates('timestamp').set_index('timestamp')
            except:
                pass
        return pd.DataFrame()

    def _init_exchange(self, name):
        cfg = {'enableRateLimit': True, 'rateLimit': 200}
        try:
            self.exchanges.append(('binance', ccxt.binance(cfg), SYMBOL_MAP))
        except Exception as e:
            logger.warning(f"Falha ao iniciar {name}: {e}")

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 1000,
    ) -> Optional[pd.DataFrame]:
        """
        Busca dados OHLCV prioritariamente do CSV local (padrão) com fallback para API.

        Args:
            symbol: Par de trading (ex: BTC/USDT)
            timeframe: Timeframe (ex: 1h, 4h, 1d)
            limit: Número de candles

        Returns:
            DataFrame com OHLCV ou None se falhar
        """
        # 1. Tenta carregar do CSV local (padrão do projeto)
        df = self._load_from_csv(symbol, timeframe, limit)
        if df is not None:
            return df

        # 2. Fallback para API da Binance
        for exch_name, exch, sym_map in self.exchanges:
            try:
                df = await self._fetch_from_exchange(exch, exch_name, symbol, timeframe, limit)
                if df is not None:
                    return df
            except Exception as e:
                logger.warning(f"{exch_name} falhou: {e}")

        logger.error(f"CSV + Binance falharam para {symbol}")
        return None

    def _load_from_csv(self, symbol, timeframe, limit):
        """Carrega dados do CSV local no repositorio."""
        name = symbol.replace('/', '_')
        for root in _ROOTS:
            csv_path = os.path.join(root, 'data', 'raw', timeframe, f'{name}.csv')
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.tail(limit).reset_index(drop=True)
                logger.info(f"OK {symbol} (CSV local): {len(df)} candles")
                return df
        logger.error(f"CSV nao encontrado para {symbol}")
        return None

    async def _fetch_from_exchange(self, exchange, name, symbol, timeframe, limit):
        """Busca dados de uma exchange com paginação."""
        all_candles = []

        while len(all_candles) < limit:
            if not all_candles:
                chunk = await self._fetch_chunk(exchange, symbol, timeframe)
            else:
                chunk = await self._fetch_chunk(
                    exchange, symbol, timeframe, end_time=all_candles[0][0] - 1
                )

            if chunk is None:
                return None
            if not chunk:
                break

            all_candles = chunk + all_candles if all_candles else chunk[:]
            if len(chunk) < MAX_PER_REQUEST:
                break

        if not all_candles:
            return None

        all_candles = all_candles[-limit:]
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        if len(df) < 10 or df['close'].isna().any():
            return None

        return df

    async def _fetch_chunk(
        self, exchange, symbol: str, timeframe: str,
        since: Optional[int] = None, end_time: Optional[int] = None
    ) -> Optional[list]:
        """Busca um chunk de até MAX_PER_REQUEST candles."""
        params = {}
        if end_time is not None:
            params['endTime'] = end_time

        for attempt in range(3):
            try:
                ohlcv = await asyncio.to_thread(
                    exchange.fetch_ohlcv,
                    symbol, timeframe, since, MAX_PER_REQUEST, params
                )
                return ohlcv if ohlcv else []
            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                if attempt < 3 and '451' in str(e):
                    raise  # Don't retry blocked locations
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                logger.error(f"Erro ao buscar chunk de {symbol} ({type(exchange).__name__}): {e}")
                return None
    
    async def fetch_multiple_symbols(
        self,
        symbols: List[str],
        timeframe: str = "1h",
        limit: int = 1000
    ) -> dict:
        tasks = [self.fetch_ohlcv(s, timeframe, limit) for s in symbols]
        results = await asyncio.gather(*tasks)
        data = {}
        for symbol, df in zip(symbols, results):
            if df is not None:
                data[symbol] = df
        return data
