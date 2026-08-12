#!/usr/bin/env bash
# FinBot v2 cutover — truncate legacy tables and apply v2 schema + seed
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_URL="${DATABASE_URL:-}"

if [ -z "$DB_URL" ]; then
  if [ -f "$ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env"
    set +a
    DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@crypto-postgres:5432/${DB_NAME}"
  else
    echo "ERROR: DATABASE_URL or .env required"
    exit 1
  fi
fi

echo "=== FinBot v2 Cutover ==="
echo "Database: postgresql://***@$(echo "$DB_URL" | sed 's|.*@||')"

psql "$DB_URL" <<'SQL'
DROP TABLE IF EXISTS trade_log CASCADE;
DROP TABLE IF EXISTS bot_settings CASCADE;
DROP TABLE IF EXISTS leme_decisions CASCADE;
DROP TABLE IF EXISTS shadow_metrics CASCADE;
DROP TABLE IF EXISTS shadow_long_scan CASCADE;
DROP TABLE IF EXISTS shadow_short_metrics CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS evaluations_log CASCADE;
DROP TABLE IF EXISTS daily_metrics CASCADE;
DROP TABLE IF EXISTS leme_shadow_long CASCADE;
DROP TABLE IF EXISTS leme_shadow_short CASCADE;
DROP TABLE IF EXISTS guardian_events CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS block_budgets CASCADE;
DROP TABLE IF EXISTS block_settings CASCADE;
DROP TABLE IF EXISTS global_settings CASCADE;
DROP TABLE IF EXISTS strategy_blocks CASCADE;
SQL

psql "$DB_URL" -f "$ROOT/infra/init/002_v2_schema.sql"
psql "$DB_URL" -f "$ROOT/infra/init/003_v2_seed.sql"

echo "=== Cutover complete ==="
