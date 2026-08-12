-- FinBot v2 — Seed inicial (Leme 100%, Mare disabled)
INSERT INTO strategy_blocks (id, name, enabled, sort_order) VALUES
    ('leme', 'Leme (Mean Reversion)', TRUE, 1),
    ('mare', 'Maré (Elder)', FALSE, 2)
ON CONFLICT (id) DO NOTHING;

INSERT INTO block_budgets (block_id, allocated_usdt, realized_pnl) VALUES
    ('leme', 10000.00, 0),
    ('mare', 0, 0)
ON CONFLICT (block_id) DO NOTHING;

INSERT INTO global_settings (key, value) VALUES
    ('dry_run', 'false'),
    ('monitor.interval_sec', '10'),
    ('bnb.min_balance_usdt', '5')
ON CONFLICT (key) DO NOTHING;

-- Leme entry gates (direction + tier)
INSERT INTO block_settings (block_id, key, value) VALUES
    ('leme', 'scan.top_n', '20'),
    ('leme', 'scan.min_volume_usdt', '10000000'),
    ('leme', 'scan.interval_sec', '900'),
    ('leme', 'entry.default_type', '"market"'),
    ('leme', 'entry.long_major_enabled', 'true'),
    ('leme', 'entry.long_strong_alt_enabled', 'true'),
    ('leme', 'entry.long_high_volatility_enabled', 'true'),
    ('leme', 'entry.short_major_enabled', 'true'),
    ('leme', 'entry.short_strong_alt_enabled', 'true'),
    ('leme', 'entry.short_high_volatility_enabled', 'true'),
    ('leme', 'entry.long_major_min_score', '0.65'),
    ('leme', 'entry.long_strong_alt_min_score', '0.65'),
    ('leme', 'entry.long_high_volatility_min_score', '0.70'),
    ('leme', 'entry.short_major_min_score', '0.85'),
    ('leme', 'entry.short_strong_alt_min_score', '0.85'),
    ('leme', 'entry.short_high_volatility_min_score', '0.85'),
    ('leme', 'entry.long_major_max_rsi', '38'),
    ('leme', 'entry.short_major_min_rsi', '65'),
    ('leme', 'entry.long_allowed_regimes', '["bull"]'),
    ('leme', 'entry.short_allowed_regimes', '["bear","neutral"]'),
    ('leme', 'entry.long_major_sl', '3.0'),
    ('leme', 'entry.long_major_tp', '3.0'),
    ('leme', 'entry.short_major_sl', '5.0'),
    ('leme', 'entry.short_major_tp', '3.0'),
    ('leme', 'exit.max_hold_hours', '12'),
    ('leme', 'exit.rsi_exit', '70'),
    ('leme', 'exit.trailing_enabled', 'false'),
    ('leme', 'exit.trailing_activation_atr', '1.0'),
    ('leme', 'exit.trailing_distance_atr', '2.0'),
    ('leme', 'exit.mode', '"software"'),
    ('leme', 'risk.max_positions', '20'),
    ('leme', 'risk.futures_enabled', 'true'),
    ('leme', 'risk.futures_max_positions', '3'),
    ('leme', 'risk.cooldown_hours', '2'),
    ('leme', 'guardian.max_consecutive_sl', '3'),
    ('leme', 'guardian.min_win_rate', '40'),
    ('leme', 'guardian.cooldown_hours', '24'),
    ('leme', 'guardian.shadow_min_trades', '5'),
    ('leme', 'guardian.shadow_min_winrate', '60'),
    ('leme', 'shadow.scan_interval_hours', '4')
ON CONFLICT (block_id, key) DO NOTHING;
