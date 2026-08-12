"""
Mean Reversion V1 - 3 features RSI, lookahead 12h.
"""
TIER = "Strong Alt"
TIMEFRAME = "15m"
CANDLES_TO_FETCH = 6400
LOOKAHEAD_CANDLES = 48

SEQ_LEN = 144
LSTM_HIDDEN = 128
LSTM_LAYERS = 1
DROPOUT = 0.3
BATCH_SIZE = 32
EPOCHS = 100
LEARNING_RATE = 0.00015

FEATURES = [
    'rsi_14', 'rsi_smooth', 'rsi_14_4h',
    'funding_rate', 'funding_change',
]
