"""
Dataset para modelo Breakout V1 (Major Tier - Donchian 15).

Estratégia Breakout:
  Detecta setups de rompimento usando canal de Donchian.
  O modelo aprende quais condições (preço no topo do canal, RSI, momentum,
  volatilidade) levam a desempenho ACIMA DA MEDIANA nas próximas horas.

Label:
  1 = max_return[t+1:t+LOOKAHEAD] > mediana de todos os retornos
  0 = retorno abaixo ou igual à mediana

Score (0-1):
  Probabilidade do candle atual ter retorno acima da mediana nas próximas horas.
  Score alto = setup breakout favorável.
  Consumido pelo fb-decision-engine (filtra >= 0.75).
"""
import logging
import numpy as np
import pandas as pd
from src.shared.base_dataset import BaseDataset
from src.shared.indicators import (
    calculate_rsi, calculate_atr, calculate_donchian_channels,
    calculate_momentum, calculate_volatility
)
from . import config

logger = logging.getLogger(__name__)


class BreakoutV1Dataset(BaseDataset):
    """
    Dataset específico para Breakout V1.
    Target: retorno acima da mediana nas próximas N horas.
    Features: Donchian, RSI, ATR, Momentum, volatilidade.
    """
    
    def __init__(self, symbol: str):
        super().__init__(symbol=symbol, tier=config.TIER)
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cria features de Breakout V1 a partir de OHLCV.
        """
        df = df.copy()
        
        logger.info(f"Criando features de Breakout V1 para {self.symbol}...")
        logger.info(f"  Entrada: {len(df)} candles")
        
        # Donchian Channels
        high, low, mid = calculate_donchian_channels(
            df['high'], df['low'], period=config.DONCHIAN_PERIOD
        )
        df['donchian_high'] = high
        df['donchian_low'] = low
        df['donchian_mid'] = mid
        
        # Posição do preço relativa ao canal
        df['price_to_high'] = df['close'] / df['donchian_high']
        df['price_to_low'] = df['close'] / df['donchian_low']
        df['donchian_range'] = df['donchian_high'] - df['donchian_low']
        df['position_in_range'] = (
            (df['close'] - df['donchian_low']) / df['donchian_range']
        )
        
        # RSI
        df['rsi'] = calculate_rsi(df['close'], period=config.RSI_PERIOD)
        
        # ATR
        df['atr'] = calculate_atr(df, period=config.ATR_PERIOD)
        
        # Volatilidade relativa
        df['volatility'] = calculate_volatility(df, period=14)
        
        # Momentum
        df['momentum'] = calculate_momentum(df['close'], period=5)
        
        logger.info(f"  Features criadas: 11 features técnicas")
        
        return df
    
    def add_target_label(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Target: 1 se o retorno máximo nas próximas N horas for
        superior à mediana de todos os retornos.
        
        Isso dá ~50% de positivos e o modelo aprende quais features
        (preço no topo do canal, RSI moderado, momentum positivo)
        antecedem desempenho acima da média.
        """
        df = df.copy()
        lookahead = config.LOOKAHEAD_HOURS
        
        # Retorno máximo nos próximos N candles (t+1 até t+lookahead)
        max_future = df['close'].shift(-1)
        for i in range(2, lookahead + 1):
            max_future = np.maximum(max_future, df['close'].shift(-i))
        
        future_return = max_future / df['close'] - 1
        
        # Target: 1 se retorno > mediana
        median_ret = future_return.median()
        df['target'] = (future_return > median_ret).astype(int)
        
        # Últimos N candles sem futuro
        df.loc[df.index[-lookahead:], 'target'] = np.nan
        
        ratio = df['target'].sum() / len(df.dropna(subset=['target']))
        logger.info(f"  Target criado: {df['target'].sum():.0f} positivos "
                    f"({ratio:.1%}) | mediana retorno: {median_ret:.4%}")
        
        return df
