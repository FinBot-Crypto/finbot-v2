"""
Cálculos de indicadores técnicos robustos para todos os modelos.
"""
import pandas as pd
import numpy as np


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcula RSI (Relative Strength Index).
    
    Args:
        close: Série de preços de fechamento
        period: Período (padrão 14)
    
    Returns:
        Série com valores de RSI
    """
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calcula ATR (Average True Range).
    
    Args:
        df: DataFrame com colunas 'high', 'low', 'close'
        period: Período (padrão 14)
    
    Returns:
        Série com valores de ATR
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_donchian_channels(high: pd.Series, low: pd.Series, period: int = 20):
    """
    Calcula Donchian Channels.
    
    Args:
        high: Série de máximas
        low: Série de mínimas
        period: Período (padrão 20)
    
    Returns:
        Tupla (high_channel, low_channel, mid_channel)
    """
    high_channel = high.rolling(window=period).max()
    low_channel = low.rolling(window=period).min()
    mid_channel = (high_channel + low_channel) / 2
    
    return high_channel, low_channel, mid_channel


def calculate_bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2):
    """
    Calcula Bollinger Bands.
    
    Args:
        close: Série de preços de fechamento
        period: Período (padrão 20)
        std_dev: Número de desvios padrão (padrão 2)
    
    Returns:
        Tupla (middle_band, upper_band, lower_band)
    """
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return sma, upper_band, lower_band


def calculate_momentum(close: pd.Series, period: int = 5) -> pd.Series:
    """
    Calcula Momentum (diferença de preço).
    
    Args:
        close: Série de preços de fechamento
        period: Período (padrão 5)
    
    Returns:
        Série com valores de momentum
    """
    return close.diff(period)


def calculate_volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Calcula SMA do volume.
    
    Args:
        volume: Série de volumes
        period: Período (padrão 20)
    
    Returns:
        Série com SMA do volume
    """
    return volume.rolling(window=period).mean()


def calculate_volatility(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Calcula volatilidade como desvio padrão dos retornos percentuais.
    
    Args:
        df: DataFrame com coluna 'close'
        period: Período (padrão 20)
    
    Returns:
        Série com valores de volatilidade
    """
    returns = df['close'].pct_change()
    volatility = returns.rolling(window=period).std()
    return volatility


def calculate_sma(close: pd.Series, period: int = 20) -> pd.Series:
    """
    Calcula SMA (Simple Moving Average).
    
    Args:
        close: Série de preços de fechamento
        period: Período (padrão 20)
    
    Returns:
        Série com valores de SMA
    """
    return close.rolling(window=period).mean()


def calculate_z_score(close: pd.Series, period: int = 20) -> pd.Series:
    """
    Calcula Z-score (desvio da média em unidades de desvio padrão).
    
    Args:
        close: Série de preços de fechamento
        period: Período (padrão 20)
    
    Returns:
        Série com valores de Z-score
    """
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    z_score = (close - sma) / std
    return z_score
