# FinBot v2

Arquitetura modular por blocos estratégicos com core de execução/monitoramento compartilhado.

## Serviços v2

| Serviço | Papel |
|---------|-------|
| `fb-leme-scan` | Universo de mercado → `leme.universe` |
| `fb-leme-engine` | ML + filtros + risk → `trade.order` |
| `fb-leme-guardian` | Pausa direction+tier |
| `fb-leme-shadow` | Simulações shadow |
| `fb-core-exec` | Executa ordens Binance → `trade.opened` |
| `fb-core-monitor` | SL/TP/time/RSI/trailing → `trade.closed` |
| `fb-core-dashboard` | UI + API |

## Cutover (big bang)

```bash
# 1. Infra
cd infra && docker compose up -d

# 2. Schema v2 (truncate legacy)
export DATABASE_URL=postgresql://user:pass@crypto-postgres:5432/crypto_bot
bash scripts/v2_cutover.sh

# 3. Subir stack v2
docker compose -f docker-compose.v2.yml --profile v2 up -d

# 4. Desligar stack legado (se ainda rodando)
docker compose down
```

## Payload trade.order

Ver `packages/finbot-common/finbot_common/payloads.py` — contrato `TradeOrder` com:
- `entry.type`: market | limit
- `exit`: SL, TP, max_hold_hours, rsi_exit, trailing, mode
- `client_order_id`: rastreio Binance
- `execution`: retries, dust tolerance

## Budget

- `block_budgets`: Leme 100% inicial, Maré disabled
- PnL isolado por bloco em `positions.block_id`

## NATS subjects v2

```
leme.universe → fb-leme-engine
trade.order   → fb-core-exec
trade.opened  → fb-core-monitor
trade.close   → fb-core-exec
trade.closed  → fb-leme-guardian
```

## finbot-common

Pacote compartilhado em `packages/finbot-common/` — payloads, indicators, settings, client_order_id.
