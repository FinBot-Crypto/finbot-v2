"""
Mean Reversion V1 - RSI + Funding Rate + OI.
Target: direcao do RSI (RSI[t+12] > RSI[t]).
"""
import logging
import numpy as np
import pandas as pd
from src.shared.base_dataset import BaseDataset
from src.shared.indicators import calculate_rsi, calculate_sma
from . import config

logger = logging.getLogger(__name__)


class MeanReversionV1Dataset(BaseDataset):

    def __init__(self, symbol: str):
        super().__init__(symbol=symbol, tier=config.TIER)
        self.funding_df = None
        self.oi_df = None

    def set_futures_data(self, funding_df=None, oi_df=None):
        self.funding_df = funding_df
        self.oi_df = oi_df
        return self

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        logger.info(f"Features para {self.symbol} ({len(df)} candles)...")

        close = df['close']

        # RSI
        tf = config.TIMEFRAME
        mult = 56 if tf == '15m' else (28 if tf == '30m' else (168 if tf == '5m' else 14))
        df['rsi_14'] = calculate_rsi(close, mult)
        df['rsi_smooth'] = df['rsi_14'].ewm(span=2, adjust=False).mean()
        r4h = 16 if tf == '15m' else (8 if tf == '30m' else (48 if tf == '5m' else 4))
        df['rsi_14_4h'] = df['rsi_14'].rolling(r4h).mean()

        df['rsi_slope'] = df['rsi_14'].diff(6)

        # Funding rate (shift do timestamp para garantir zero lookahead)
        if self.funding_df is not None and len(self.funding_df) > 0:
            fd = self.funding_df.copy()
            fd.index = fd.index + pd.Timedelta(hours=8)  # funding so vale pro futuro
            df_ts = df.set_index('timestamp')
            df_ts = df_ts.join(fd[['fundingRate']], how='left')
            df_ts['funding_rate'] = df_ts['fundingRate'].ffill()
            df_ts['funding_change'] = df_ts['funding_rate'].diff()
            df = df_ts.drop(columns=['fundingRate']).reset_index()
        else:
            df['funding_rate'] = np.nan
            df['funding_change'] = np.nan

        # Open interest (shift do timestamp)
        if self.oi_df is not None and len(self.oi_df) > 0:
            oi = self.oi_df.copy()
            oi.index = oi.index + pd.Timedelta(hours=1)  # OI so vale 1h depois
            df_ts = df.set_index('timestamp')
            df_ts = df_ts.join(oi[['openInterestValue']], how='left')
            df_ts['open_interest'] = df_ts['openInterestValue'].ffill()
            df_ts['oi_change_1h'] = df_ts['open_interest'].pct_change()
            df_ts['oi_change_24h'] = df_ts['open_interest'].pct_change(24)
            df = df_ts.drop(columns=['openInterestValue']).reset_index()
        else:
            df['open_interest'] = np.nan
            df['oi_change_1h'] = np.nan
            df['oi_change_24h'] = np.nan

        # Manter apenas features configuradas + essenciais
        keep = config.FEATURES + ['timestamp', 'close']
        return df[[c for c in keep if c in df.columns]].ffill()

    def add_target_label(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Target: 1 se RSI estiver MAIOR em LOOKAHEAD_CANDLES (48 = 12h).
        RSI autocorrelacao ~0.99 -> target mais previsivel que preco.
        Score = predict_proba.
        """
        df = df.copy()
        la = config.LOOKAHEAD_CANDLES

        future_rsi = df['rsi_smooth'].shift(-la)
        df['target'] = (future_rsi > df['rsi_smooth']).astype(float)
        df.loc[df.index[-la:], 'target'] = np.nan

        pos = df['target'].sum()
        n = len(df.dropna(subset=['target']))
        logger.info(f"  Target RSI: {pos:.0f} sobe ({pos/max(n,1):.1%}) de {n} | "
                    f"autocorr={df['rsi_smooth'].autocorr():.3f}")

        return df

    def _features_1h(self, df):
        close, high, low, vol = df['close'], df['high'], df['low'], df['volume']
        df['rsi_14'] = calculate_rsi(close, 14)
        df['rsi_smooth'] = df['rsi_14'].ewm(span=2, adjust=False).mean()
        return df
