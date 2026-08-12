"""
Configuração específica do modelo Breakout V1 (Major Tier).
"""

# Tier
TIER = "Major"

# Features
DONCHIAN_PERIOD = 15
RSI_PERIOD = 14
ATR_PERIOD = 14

# Modelo RandomForest (regularizado para evitar overfitting)
N_ESTIMATORS = 80
MAX_DEPTH = 4
MIN_SAMPLES_SPLIT = 25
MIN_SAMPLES_LEAF = 15

# Target Breakout
# 1 = retorno máximo em LOOKAHEAD_HOURS > mediana de todos os retornos
LOOKAHEAD_HOURS = 8

# Features utilizadas
FEATURES = [
    'donchian_high',
    'donchian_low',
    'donchian_mid',
    'price_to_high',
    'price_to_low',
    'rsi',
    'atr',
    'volatility',
    'momentum',
    'donchian_range',
    'position_in_range'
]
