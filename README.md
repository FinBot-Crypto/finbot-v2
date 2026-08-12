# FinBot v2 — Monorepo

Stack unificada: core + Leme + ML offline.

## Deploy

Push em `main` dispara o workflow **Deploy v2 Stack** no runner self-hosted da VPS Oracle.

Manual na VPS:

```bash
cd /root/crypto-bot
bash scripts/v2_cutover.sh   # primeira vez apenas
docker compose up -d --build
```

## Serviços

| Container | Papel |
|-----------|-------|
| fb-leme-scan | Universo → `leme.universe` |
| fb-leme-engine | ML + risk → `trade.order` |
| fb-leme-guardian | Pausa direction+tier |
| fb-leme-shadow | Shadow LONG/SHORT |
| fb-core-exec | Execução Binance |
| fb-core-monitor | Fechamento SL/TP/time/RSI/trailing |
| fb-core-dashboard | UI :8000 |
| fb-ml-training | Treino offline |
| fb-ml-validation | Validação offline |

## Infra

PostgreSQL + NATS via [`fb-infra`](https://github.com/FinBot-Crypto/fb-infra).
