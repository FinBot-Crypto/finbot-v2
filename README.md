# FinBot v2

Monorepo de produção: **core + Leme + ML offline**.

Repositório: [FinBot-Crypto/finbot-v2](https://github.com/FinBot-Crypto/finbot-v2)

## Workspace local

Este diretório **é** o clone do `finbot-v2`. Deve conter apenas:

```
financas_crypto_bot/          (= finbot-v2)
├── packages/finbot-common/
├── services/fb-core-*        core-exec, core-monitor, core-dashboard
├── services/fb-leme-*        scan, engine, guardian, shadow
├── services/fb-ml-*          training, validation
├── scripts/migrations/       SQL v2
├── docker-compose.yml
├── .env.example
└── .github/workflows/deploy.yml
```

## Setup local

```bash
git clone https://github.com/FinBot-Crypto/finbot-v2.git financas_crypto_bot
cd financas_crypto_bot
cp .env.example .env          # editar secrets

# Infra (repo separado)
git clone https://github.com/FinBot-Crypto/fb-infra.git infra
cd infra && cp .env.example .env && docker compose up -d
```

## Deploy produção (VPS Oracle)

Push em `main` → GitHub Actions (runner self-hosted) → `/root/crypto-bot`

```bash
ssh oracle
cd /root/crypto-bot
docker compose --env-file .env ps
```

Cutover DB (uma vez):

```bash
bash scripts/v2_cutover.sh
```

## Repositórios da org

| Repo | Status |
|------|--------|
| **finbot-v2** | Ativo — este repo |
| **fb-infra** | Ativo — Postgres + NATS |
| **.github** | Legado (workflows antigos) |
| fb-* (11 repos) | **Arquivados** — substituídos pelo monorepo |

## Serviços

| Container | Papel |
|-----------|-------|
| fb-leme-scan | `leme.universe` |
| fb-leme-engine | ML + risk → `trade.order` |
| fb-leme-guardian | Pausa direction+tier |
| fb-leme-shadow | Shadow simulações |
| fb-core-exec | Execução Binance |
| fb-core-monitor | Fechamento SL/TP/time/RSI/trailing |
| fb-core-dashboard | UI :8000 |
| fb-ml-training / validation | ML offline |

Ver [V2_README.md](V2_README.md) para contratos NATS e payload `TradeOrder`.
