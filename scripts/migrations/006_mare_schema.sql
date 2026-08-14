-- Maré observability and default settings. Keeps live trading disabled.
CREATE TABLE IF NOT EXISTS mare_signals (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10),
    score FLOAT NOT NULL,
    accepted BOOLEAN NOT NULL DEFAULT FALSE,
    reason VARCHAR(64) NOT NULL,
    tide_state VARCHAR(16) NOT NULL,
    wave_state VARCHAR(16) NOT NULL,
    ripple_state VARCHAR(16) NOT NULL,
    price NUMERIC(18, 8) NOT NULL,
    atr NUMERIC(18, 8) NOT NULL DEFAULT 0,
    block_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    live_orders_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    payload JSONB NOT NULL DEFAULT '{}',
    evaluated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mare_signals_time ON mare_signals(evaluated_at DESC);
CREATE INDEX IF NOT EXISTS idx_mare_signals_symbol ON mare_signals(symbol, evaluated_at DESC);

INSERT INTO block_settings (block_id, key, value) VALUES
    ('mare', 'mare.min_score', '0.65'),
    ('mare', 'mare.tide_timeframe', '"4h"'),
    ('mare', 'mare.wave_timeframe', '"1h"'),
    ('mare', 'mare.ripple_timeframe', '"15m"'),
    ('mare', 'mare.live_orders_enabled', 'false')
ON CONFLICT (block_id, key) DO NOTHING;
