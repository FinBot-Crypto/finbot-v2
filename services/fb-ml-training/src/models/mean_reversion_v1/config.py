"""
Mean Reversion V1 - Configurações por Tier e Direção.
Timeframe: 5m.
"""
TIER = "Major"
DIRECTION = "long"
TIMEFRAME = "15m"
CANDLES_TO_FETCH = 80000  # Usar o limite total do dataset robusto de 15m (80k)

# Padrões globais (serão sobrescritos dinamicamente durante o treino)
LOOKAHEAD_CANDLES = 96  # 24h em velas de 15m
TP_PCT = 1.0
SEQ_LEN = 96  # 24h de histórico de comportamento
LSTM_HIDDEN = 32
LSTM_LAYERS = 1
DROPOUT = 0.4
BATCH_SIZE = 64
EPOCHS = 100
LEARNING_RATE = 0.0001
WEIGHT_DECAY = 1e-2

FEATURES = [
    'rsi_14', 'rsi_smooth', 'rsi_14_4h',
    'btc_rsi_14',
    'bb_zscore',
    'volume_zscore',
    'macro_trend_200',
    'macro_zscore_200',
    'volatility_50',
    'btc_macro_zscore'
]

# Mapeamento completo dos hiperparâmetros dos 6 modelos (1:1 simétrico)
CONFIG_MAP = {
    "Major": {
        "long": {
            "TP_PCT": 0.8,
            "LOOKAHEAD_CANDLES": 96,  # 24h
            "SEQ_LEN": 96,
            "LSTM_HIDDEN": 32,
            "LSTM_LAYERS": 1,
            "DROPOUT": 0.4,
            "BATCH_SIZE": 64,
            "LEARNING_RATE": 0.0001,
            "WEIGHT_DECAY": 1e-2,
        },
        "short": {
            "TP_PCT": 0.8,
            "LOOKAHEAD_CANDLES": 96,
            "SEQ_LEN": 96,
            "LSTM_HIDDEN": 32,
            "LSTM_LAYERS": 1,
            "DROPOUT": 0.4,
            "BATCH_SIZE": 64,
            "LEARNING_RATE": 0.0001,
            "WEIGHT_DECAY": 1e-2,
        }
    },
    "Strong Alt": {
        "long": {
            "TP_PCT": 1.0,
            "LOOKAHEAD_CANDLES": 96,  # 24h
            "SEQ_LEN": 96,
            "LSTM_HIDDEN": 48,
            "LSTM_LAYERS": 1,
            "DROPOUT": 0.4,
            "BATCH_SIZE": 64,
            "LEARNING_RATE": 0.0001,
            "WEIGHT_DECAY": 1e-2,
        },
        "short": {
            "TP_PCT": 1.0,
            "LOOKAHEAD_CANDLES": 96,
            "SEQ_LEN": 96,
            "LSTM_HIDDEN": 48,
            "LSTM_LAYERS": 1,
            "DROPOUT": 0.4,
            "BATCH_SIZE": 64,
            "LEARNING_RATE": 0.0001,
            "WEIGHT_DECAY": 1e-2,
        }
    },
    "High Volatility": {
        "long": {
            "TP_PCT": 1.5,
            "LOOKAHEAD_CANDLES": 96,  # 24h
            "SEQ_LEN": 96,
            "LSTM_HIDDEN": 48,
            "LSTM_LAYERS": 1,
            "DROPOUT": 0.5,
            "BATCH_SIZE": 64,
            "LEARNING_RATE": 0.0001,
            "WEIGHT_DECAY": 2e-2,
        },
        "short": {
            "TP_PCT": 1.5,
            "LOOKAHEAD_CANDLES": 96,
            "SEQ_LEN": 96,
            "LSTM_HIDDEN": 48,
            "LSTM_LAYERS": 1,
            "DROPOUT": 0.5,
            "BATCH_SIZE": 64,
            "LEARNING_RATE": 0.0001,
            "WEIGHT_DECAY": 2e-2,
        }
    }
}

def get_parameter(param_name: str, tier: str = None, direction: str = "long") -> any:
    if tier is None:
        tier = TIER
    direction = direction.lower()
    tier_config = CONFIG_MAP.get(tier, CONFIG_MAP["Major"])
    dir_config = tier_config.get(direction, tier_config["long"])
    return dir_config.get(param_name)
