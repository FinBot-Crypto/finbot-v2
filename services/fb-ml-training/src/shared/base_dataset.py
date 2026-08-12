"""
Classe base abstrata para todos os datasets de modelos.
"""
import logging
import pandas as pd
from abc import ABC, abstractmethod
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class BaseDataset(ABC):
    """
    Classe base abstrata para criação de datasets.
    Cada modelo concreto herda e implementa create_features().
    """
    
    def __init__(self, symbol: str, tier: str):
        """
        Inicializa o dataset.
        
        Args:
            symbol: Par de trading (ex: BTC/USDT)
            tier: Tier do ativo (Major, Strong Alt, High Volatility)
        """
        self.symbol = symbol
        self.tier = tier
        logger.info(f"Dataset inicializado: {symbol} ({tier})")
    
    @abstractmethod
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Deve ser implementado por cada modelo.
        Transforma OHLCV em features + target.
        
        Args:
            df: DataFrame com OHLCV
        
        Returns:
            DataFrame com features + coluna 'target'
        """
        pass
    
    def add_target_label(
        self,
        df: pd.DataFrame,
        lookahead_hours: int = 4,
        return_pct: float = 0.0
    ) -> pd.DataFrame:
        """
        Adiciona coluna 'target' com label binário.
        Target = 1 se preço subir nas próximas lookahead_hours (direção positiva)
        Target = 0 se preço cair ou ficar igual
        
        Args:
            df: DataFrame com 'close'
            lookahead_hours: Horas para lookahead (candles com timeframe 1h)
            return_pct: Percentual mínimo de retorno (0 = qualquer alta)
        
        Returns:
            DataFrame com coluna 'target' adicionada
        """
        df = df.copy()
        
        future_close = df['close'].shift(-lookahead_hours)
        
        if return_pct > 0:
            df['target'] = (
                (future_close > df['close'] * (1 + return_pct / 100))
            ).astype(int)
        else:
            df['target'] = (future_close > df['close']).astype(int)
        
        df.loc[df.index[-lookahead_hours:], 'target'] = pd.NA
        
        return df
    
    def prepare(
        self,
        df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Pipeline completo: criar features + target + separar train/val.
        Cada modelo define seus próprios defaults de target via add_target_label().
        
        Args:
            df: DataFrame com OHLCV
        
        Returns:
            Tupla (X_train, X_val, y_train, y_val)
        """
        # 1. Criar features
        logger.info(f"Criando features para {self.symbol}...")
        df = self.create_features(df)
        
        # 2. Adicionar target (cada modelo define seus parâmetros)
        logger.info(f"Adicionando target label...")
        df = self.add_target_label(df)
        
        # 3. Remover NaNs
        logger.info(f"Removendo NaNs...")
        initial_rows = len(df)
        df = df.dropna()
        logger.info(f"Removidas {initial_rows - len(df)} linhas com NaN")
        
        if len(df) < 100:
            raise ValueError(f"Dados insuficientes após limpeza: {len(df)} linhas")
        
        # 4. Separar features e target
        drop_cols = ['target', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
        X = df.drop(columns=[c for c in drop_cols if c in df.columns])
        y = df['target']
        
        # 5. Walk-forward split: 70% train, 30% validação (temporal)
        split_idx = int(len(X) * 0.7)
        X_train = X.iloc[:split_idx]
        X_val = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_val = y.iloc[split_idx:]
        
        # 6. Normalizar features com stats do TREINO (sem data leakage)
        mean, std = X_train.mean(), X_train.std()
        # Evita divisão por zero para features constantes (ex: OI em altcoins que não possuem CSV de OI)
        std = std.replace(0, 1.0).fillna(1.0)
        X_train = (X_train - mean) / std
        X_val = (X_val - mean) / std
        
        logger.info(f"OK Dataset pronto: {len(X_train)} train, {len(X_val)} val")
        logger.info(f"  Target stats: train média={y_train.mean():.4%} val média={y_val.mean():.4%}")
        
        return X_train, X_val, y_train, y_val
