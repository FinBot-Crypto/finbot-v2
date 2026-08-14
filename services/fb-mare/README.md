# fb-mare

Motor independente da estratégia Maré para o ecossistema FinBot.

A Maré analisa a mesma moeda em três horizontes:

- Maré: tendência dominante em 4h;
- Onda: pullback/oportunidade em 1h;
- Marola: gatilho de timing em 15m.

O serviço consome a seleção publicada pelo `fb-leme-scan` em `leme.universe`, grava cada análise em `mare_signals` e só publica `trade.order` quando o bloco `mare` está habilitado e `mare.live_orders_enabled=true`. Assim ele pode operar em shadow/observabilidade sem risco de enviar ordens reais.

## Arquitetura

```text
leme.universe -> fb-mare -> mare_signals
                     |
                     +--(gate mare habilitado)---> trade.order
                                                     |
                                  fb-core-exec -> fb-core-monitor
```

O contrato de ordem é compatível com `finbot-common` e carrega `block_id="mare"`. O serviço não executa ordens diretamente.

## Configuração padrão segura

```text
MARE_UNIVERSE_SUBJECT=leme.universe
MARE_LIVE_ORDERS_ENABLED=false
MARE_NOTIONAL_USDT=10
MARE_MIN_SCORE=0.65
MARE_TIDE_TIMEFRAME=4h
MARE_WAVE_TIMEFRAME=1h
MARE_RIPPLE_TIMEFRAME=15m
```

O bloco também precisa estar `strategy_blocks.enabled=true` no banco. A instalação inicial mantém `mare` desabilitado até que os sinais shadow sejam validados.

## Desenvolvimento

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
```

## Deploy

O Dockerfile foi desenhado para ser construído a partir da raiz do checkout do FinBot v2, onde `packages/finbot-common` está disponível:

```bash
docker build -f fb-mare/Dockerfile .
```

As migrações em `migrations/001_mare_schema.sql` criam a tabela de sinais e as configurações namespaced do bloco.
