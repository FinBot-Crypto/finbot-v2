"""
Mean Reversion V1 - RSI + Funding Rate + OI.
Target: direcao do RSI (RSI[t+12] > RSI[t]).
"""
import logging
import numpy as np
import pandas as pd
from src.shared.base_dataset import BaseDataset
from src.shared.indicators import calculate_rsi, calculate_sma, calculate_volatility
from . import config

logger = logging.getLogger(__name__)


class MeanReversionV1Dataset(BaseDataset):

    def __init__(self, symbol: str, direction: str = "long"):
        super().__init__(symbol=symbol, tier=config.TIER)
        self.funding_df = None
        self.oi_df = None
        self.btc_df = None
        self.direction = direction.lower()

    def set_futures_data(self, funding_df=None, oi_df=None):
        self.funding_df = funding_df
        self.oi_df = oi_df
        return self

    def set_btc_data(self, btc_df=None):
        self.btc_df = btc_df
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

        # BB Z-Score (desvio do close em relação à BB)
        sma20 = calculate_sma(close, 20)
        std20 = close.rolling(window=20).std()
        df['bb_zscore'] = (close - sma20) / std20.replace(0, 1.0).fillna(1.0)

        # Volume Z-Score (picos de volume)
        volume = df['volume']
        sma50_vol = volume.rolling(window=50).mean()
        std50_vol = volume.rolling(window=50).std()
        df['volume_zscore'] = (volume - sma50_vol) / std50_vol.replace(0, 1.0).fillna(1.0)

        # Macro Regime Features
        sma200 = calculate_sma(close, 200)
        std200 = close.rolling(window=200).std()
        df['macro_trend_200'] = (close / sma200.replace(0, 1.0).fillna(1.0) - 1)
        df['macro_zscore_200'] = (close - sma200) / std200.replace(0, 1.0).fillna(1.0)
        df['volatility_50'] = calculate_volatility(df, 50).fillna(0.0)

        # BTC features (estacionárias)
        if self.symbol == 'BTC/USDT':
            df['btc_rsi_14'] = calculate_rsi(df['close'], mult)
            df['btc_macro_zscore'] = df['macro_zscore_200']
        else:
            if self.btc_df is not None and len(self.btc_df) > 0:
                btc = self.btc_df.copy()
                btc['btc_rsi_14'] = calculate_rsi(btc['close'], mult)
                btc_sma200 = calculate_sma(btc['close'], 200)
                btc_std200 = btc['close'].rolling(window=200).std()
                btc['btc_macro_zscore'] = (btc['close'] - btc_sma200) / btc_std200.replace(0, 1.0).fillna(1.0)
                df_ts = df.set_index('timestamp')
                df_ts = df_ts.join(btc.set_index('timestamp')[['btc_rsi_14', 'btc_macro_zscore']], how='left')
                df = df_ts.reset_index()
            else:
                df['btc_rsi_14'] = np.nan
                df['btc_macro_zscore'] = np.nan

        # Manter apenas features configuradas + essenciais
        keep = config.FEATURES + ['timestamp', 'close', 'high', 'low']
        return df[[c for c in keep if c in df.columns]].ffill()

    def add_target_label(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Target: 1 se o preço bater o TP primeiro, 0 se bater o SL primeiro (ou se der timeout)
        nas próximas LOOKAHEAD_CANDLES.
        """
        df = df.copy()
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        n = len(df)

        la = config.LOOKAHEAD_CANDLES
        tp_sl = config.TP_PCT / 100.0 # Relação simétrica 1:1

        targets = np.zeros(n)

        # Para cada candle i, olha para a frente até i + la
        for i in range(n):
            if i >= n - la:
                targets[i] = np.nan
                continue

            entry_price = close[i]
            tp_target = entry_price * (1 + tp_sl) if self.direction == "long" else entry_price * (1 - tp_sl)
            sl_target = entry_price * (1 - tp_sl) if self.direction == "long" else entry_price * (1 + tp_sl)

            outcome = 0 # default é 0 (timeout ou SL primeiro)

            for step in range(1, la + 1):
                curr_idx = i + step
                curr_high = high[curr_idx]
                curr_low = low[curr_idx]

                if self.direction == "long":
                    # Tocou no SL primeiro?
                    if curr_low <= sl_target:
                        outcome = 0
                        break
                    # Tocou no TP?
                    if curr_high >= tp_target:
                        outcome = 1
                        break
                else:
                    # SHORT: Tocou no SL?
                    if curr_high >= sl_target:
                        outcome = 0
                        break
                    # SHORT: Tocou no TP?
                    if curr_low <= tp_target:
                        outcome = 1
                        break

            targets[i] = outcome

        df['target'] = targets
        df.loc[df.index[-la:], 'target'] = np.nan

        # Logs estatísticos
        valid_targets = df['target'].dropna()
        pos = valid_targets.sum()
        total_valid = len(valid_targets)
        logger.info(f"  Target: {pos:.0f} bateu TP (1:1 simetrico) ({pos/max(total_valid,1):.1%}) de {total_valid}")

        return df

    def _features_1h(self, df):
        close, high, low, vol = df['close'], df['high'], df['low'], df['volume']
        df['rsi_14'] = calculate_rsi(close, 14)
        df['rsi_smooth'] = df['rsi_14'].ewm(span=2, adjust=False).mean()
        return df
