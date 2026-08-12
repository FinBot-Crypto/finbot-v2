-- =============================================================
-- FinBot v2 — Schema (fresh start)
-- Run manually on cutover or via init script after truncate
-- =============================================================

CREATE TABLE IF NOT EXISTS strategy_blocks (
    id          VARCHAR(32) PRIMARY KEY,
    name        VARCHAR(64) NOT NULL,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS block_settings (
    block_id    VARCHAR(32) NOT NULL REFERENCES strategy_blocks(id) ON DELETE CASCADE,
    key         VARCHAR(128) NOT NULL,
    value       JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (block_id, key)
);

CREATE TABLE IF NOT EXISTS global_settings (
    key         VARCHAR(128) PRIMARY KEY,
    value       JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS block_budgets (
    block_id        VARCHAR(32) PRIMARY KEY REFERENCES strategy_blocks(id) ON DELETE CASCADE,
    allocated_usdt  NUMERIC(18, 2) NOT NULL DEFAULT 0,
    realized_pnl    NUMERIC(18, 8) NOT NULL DEFAULT 0,
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
    id                  UUID PRIMARY KEY,
    block_id            VARCHAR(32) NOT NULL REFERENCES strategy_blocks(id),
    client_order_id     VARCHAR(36),
    strategy            VARCHAR(64) NOT NULL,
    symbol              VARCHAR(20) NOT NULL,
    direction           VARCHAR(10) NOT NULL,
    tier                VARCHAR(32),
    venue               VARCHAR(16) NOT NULL DEFAULT 'spot',
    leverage            INTEGER NOT NULL DEFAULT 1,
    entry_type          VARCHAR(16) NOT NULL DEFAULT 'market',
    entry_price         NUMERIC(18, 8) NOT NULL,
    quantity            NUMERIC(18, 8) NOT NULL,
    quantity_exit       NUMERIC(18, 8),
    sl_price            NUMERIC(18, 8),
    tp_price            NUMERIC(18, 8),
    exit_config         JSONB NOT NULL DEFAULT '{}',
    signal_meta         JSONB NOT NULL DEFAULT '{}',
    status              VARCHAR(16) NOT NULL DEFAULT 'OPEN',
    exit_price          NUMERIC(18, 8),
    exit_reason         VARCHAR(32),
    pnl_pct             NUMERIC(10, 4),
    hold_hours          NUMERIC(10, 4),
    exchange_order_id   VARCHAR(64),
    close_order_id      VARCHAR(64),
    dry_run             BOOLEAN NOT NULL DEFAULT FALSE,
    opened_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_open_unique
    ON positions (block_id, symbol, direction, venue)
    WHERE status = 'OPEN';

CREATE INDEX IF NOT EXISTS idx_positions_block_status ON positions(block_id, status);
CREATE INDEX IF NOT EXISTS idx_positions_opened_at ON positions(opened_at DESC);

CREATE TABLE IF NOT EXISTS guardian_events (
    id          SERIAL PRIMARY KEY,
    block_id    VARCHAR(32) NOT NULL REFERENCES strategy_blocks(id),
    action      VARCHAR(16) NOT NULL,
    reason      TEXT,
    scope       VARCHAR(64) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_guardian_events_block ON guardian_events(block_id, created_at DESC);

CREATE TABLE IF NOT EXISTS leme_shadow_long (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(20) NOT NULL,
    tier        VARCHAR(32),
    rsi_entry   FLOAT,
    hour_entry  INTEGER,
    entry_price NUMERIC(18, 8),
    sl          FLOAT,
    tp          FLOAT,
    pnl         FLOAT,
    exit_reason VARCHAR(32),
    minutes     INTEGER,
    entry_ts    TIMESTAMP NOT NULL,
    model_score FLOAT,
    btc_trend   VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_leme_shadow_long_ts ON leme_shadow_long(entry_ts DESC);
CREATE INDEX IF NOT EXISTS idx_leme_shadow_long_tier ON leme_shadow_long(tier);

CREATE TABLE IF NOT EXISTS leme_shadow_short (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(20) NOT NULL,
    tier        VARCHAR(32),
    rsi_entry   FLOAT,
    hour_entry  INTEGER,
    entry_price NUMERIC(18, 8),
    sl          FLOAT,
    tp          FLOAT,
    pnl         FLOAT,
    exit_reason VARCHAR(32),
    minutes     INTEGER,
    entry_ts    TIMESTAMP NOT NULL,
    model_score FLOAT,
    btc_trend   VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_leme_shadow_short_ts ON leme_shadow_short(entry_ts DESC);
CREATE INDEX IF NOT EXISTS idx_leme_shadow_short_tier ON leme_shadow_short(tier);

CREATE TABLE IF NOT EXISTS evaluations_log (
    id          SERIAL PRIMARY KEY,
    block_id    VARCHAR(32) NOT NULL DEFAULT 'leme',
    symbol      VARCHAR(20) NOT NULL,
    tier        VARCHAR(32),
    strategy    VARCHAR(64),
    direction   VARCHAR(10),
    score       FLOAT,
    rsi         FLOAT,
    regime      VARCHAR(16),
    decision    VARCHAR(32),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evaluations_log_created ON evaluations_log(created_at DESC);

CREATE TABLE IF NOT EXISTS daily_metrics (
    id              SERIAL PRIMARY KEY,
    block_id        VARCHAR(32) NOT NULL DEFAULT 'leme',
    date            DATE NOT NULL,
    total_trades    INTEGER DEFAULT 0,
    winning_trades  INTEGER DEFAULT 0,
    losing_trades   INTEGER DEFAULT 0,
    total_pnl       NUMERIC(18, 8) DEFAULT 0,
    win_rate        NUMERIC(5, 2) DEFAULT 0,
    max_drawdown    NUMERIC(8, 4) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (block_id, date)
);

COMMENT ON TABLE positions IS 'Posições abertas/fechadas por bloco estratégico (v2)';
COMMENT ON TABLE block_settings IS 'Configurações namespaced por bloco (leme, mare, ...)';
