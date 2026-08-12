"""
Configurações globais e por-tier para os modelos de ML.
"""
import os
from dataclasses import dataclass
from typing import Dict

# Configurações de Ambiente
BINANCE_TESTNET = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "data"))
MODELS_DIR = os.getenv("MODELS_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "models"))
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")

# Criar diretórios se não existirem
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Configurações Gerais
TIMEFRAME = "1h"
CANDLES_TO_FETCH = 1000  # Aproximadamente 41 dias de histórico
TARGET_RETURN_PCT = 1.0  # 1% de retorno esperado
TARGET_LOOKAHEAD_HOURS = 4  # Próximas 4 horas

# TIERS DE ATIVOS
MAJOR_TIER_SYMBOLS = ["BTC/USDT", "ETH/USDT"]
STRONG_ALT_SYMBOLS = ["SOL/USDT", "MATIC/USDT", "AVAX/USDT", "LINK/USDT", "DOGE/USDT", "ADA/USDT", "XRP/USDT"]
HIGH_VOL_SYMBOLS = ["ARB/USDT", "OP/USDT", "LDO/USDT", "ATOM/USDT", "NEAR/USDT", "INJ/USDT", "PEPE/USDT", "SHIB/USDT", "MEME/USDT", "GALA/USDT"]

# Tier Mapping
TIER_SYMBOLS = {
    "Major": MAJOR_TIER_SYMBOLS,
    "Strong Alt": STRONG_ALT_SYMBOLS,
    "High Volatility": HIGH_VOL_SYMBOLS,
}


@dataclass
class BreakoutConfig:
    """Configuração para modelos Breakout"""
    
    # V1 (Major)
    V1_DONCHIAN_PERIOD = 15
    V1_RSI_PERIOD = 14
    V1_N_ESTIMATORS = 150
    V1_MAX_DEPTH = 6
    V1_MIN_SAMPLES_SPLIT = 20
    
    # V2 (Strong Alt)
    V2_DONCHIAN_PERIOD = 20
    V2_RSI_PERIOD = 14
    V2_N_ESTIMATORS = 100
    V2_MAX_DEPTH = 5
    V2_MIN_SAMPLES_SPLIT = 15
    
    # V3 (High Volatility)
    V3_DONCHIAN_PERIOD = 30
    V3_RSI_PERIOD = 14
    V3_N_ESTIMATORS = 80
    V3_MAX_DEPTH = 4
    V3_MIN_SAMPLES_SPLIT = 10
    
    @staticmethod
    def get_config(version: str) -> Dict:
        """Retorna config específica da versão"""
        if version == "v1":
            return {
                "donchian_period": BreakoutConfig.V1_DONCHIAN_PERIOD,
                "rsi_period": BreakoutConfig.V1_RSI_PERIOD,
                "n_estimators": BreakoutConfig.V1_N_ESTIMATORS,
                "max_depth": BreakoutConfig.V1_MAX_DEPTH,
                "min_samples_split": BreakoutConfig.V1_MIN_SAMPLES_SPLIT,
            }
        elif version == "v2":
            return {
                "donchian_period": BreakoutConfig.V2_DONCHIAN_PERIOD,
                "rsi_period": BreakoutConfig.V2_RSI_PERIOD,
                "n_estimators": BreakoutConfig.V2_N_ESTIMATORS,
                "max_depth": BreakoutConfig.V2_MAX_DEPTH,
                "min_samples_split": BreakoutConfig.V2_MIN_SAMPLES_SPLIT,
            }
        elif version == "v3":
            return {
                "donchian_period": BreakoutConfig.V3_DONCHIAN_PERIOD,
                "rsi_period": BreakoutConfig.V3_RSI_PERIOD,
                "n_estimators": BreakoutConfig.V3_N_ESTIMATORS,
                "max_depth": BreakoutConfig.V3_MAX_DEPTH,
                "min_samples_split": BreakoutConfig.V3_MIN_SAMPLES_SPLIT,
            }
        else:
            raise ValueError(f"Versão desconhecida: {version}")


@dataclass
class MeanReversionConfig:
    """Configuração para modelos Mean Reversion"""
    
    # V1 (Major)
    V1_SMA_PERIOD = 20
    V1_RSI_PERIOD = 14
    V1_N_ESTIMATORS = 150
    V1_MAX_DEPTH = 6
    V1_MIN_SAMPLES_SPLIT = 20
    
    # V2 (Strong Alt)
    V2_SMA_PERIOD = 30
    V2_RSI_PERIOD = 14
    V2_N_ESTIMATORS = 100
    V2_MAX_DEPTH = 5
    V2_MIN_SAMPLES_SPLIT = 15
    
    # V3 (High Volatility)
    V3_SMA_PERIOD = 40
    V3_RSI_PERIOD = 14
    V3_N_ESTIMATORS = 80
    V3_MAX_DEPTH = 4
    V3_MIN_SAMPLES_SPLIT = 10
    
    @staticmethod
    def get_config(version: str) -> Dict:
        """Retorna config específica da versão"""
        if version == "v1":
            return {
                "sma_period": MeanReversionConfig.V1_SMA_PERIOD,
                "rsi_period": MeanReversionConfig.V1_RSI_PERIOD,
                "n_estimators": MeanReversionConfig.V1_N_ESTIMATORS,
                "max_depth": MeanReversionConfig.V1_MAX_DEPTH,
                "min_samples_split": MeanReversionConfig.V1_MIN_SAMPLES_SPLIT,
            }
        elif version == "v2":
            return {
                "sma_period": MeanReversionConfig.V2_SMA_PERIOD,
                "rsi_period": MeanReversionConfig.V2_RSI_PERIOD,
                "n_estimators": MeanReversionConfig.V2_N_ESTIMATORS,
                "max_depth": MeanReversionConfig.V2_MAX_DEPTH,
                "min_samples_split": MeanReversionConfig.V2_MIN_SAMPLES_SPLIT,
            }
        elif version == "v3":
            return {
                "sma_period": MeanReversionConfig.V3_SMA_PERIOD,
                "rsi_period": MeanReversionConfig.V3_RSI_PERIOD,
                "n_estimators": MeanReversionConfig.V3_N_ESTIMATORS,
                "max_depth": MeanReversionConfig.V3_MAX_DEPTH,
                "min_samples_split": MeanReversionConfig.V3_MIN_SAMPLES_SPLIT,
            }
        else:
            raise ValueError(f"Versão desconhecida: {version}")
