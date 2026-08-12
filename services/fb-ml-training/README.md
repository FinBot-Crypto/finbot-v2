# fb-ml-training

Serviço de treinamento de **modelos LSTM** para predição de reversão à média em criptomoedas.

## Modelos

| Modelo | Tier | Ativos | Features | AUC |
|--------|------|--------|----------|-----|
| **mean_reversion_v1** | Major | BTC, ETH | RSI 14/24/4h | **0.83** |
| **mean_reversion_v2** | Strong Alt | 7 ativos | RSI 14/24/4h | ⏳ |
| **mean_reversion_v3** | High Vol | 10 ativos | RSI 14/24/4h | ⏳ |

## Arquitetura

```
src/models/mean_reversion_v1/
├── config.py       # Hiperparâmetros (timeframe, features, LSTM)
├── dataset.py      # Features + target (RSI sobe/desce em 12h)
├── lstm_train.py   # LSTM 1 layer, early stopping
└── evaluate.py     # Script de treino (não usado - usar _test_lstm.py)

src/shared/
├── data_fetcher.py # OHLCV + funding rate + CSV fallback
├── indicators.py   # RSI, SMA, Bollinger, ATR
├── base_dataset.py # Normalização z-score
├── config.py       # Constantes globais (símbolos, tiers)

data/raw/           # CSVs de OHLCV + funding rate
models/             # Modelos .pt salvos
```

## Performance (V1 - BTC + ETH)

| Métrica | Valor |
|---|---|
| AUC validação | 0.83 |
| Scores min/max | 0.02 / 0.98 |
| Target | RSI sobe/desce em 12h |
| Features | rsi_14, rsi_smooth, rsi_14_4h |
| Early stop | Época 5-10 |

### Threshold para produção

| Config | Filtro | Sinais/dia | WR | Lucro/5dias |
|--------|--------|-----------|-----|------------|
| Arrojado | RSI < 38 + score >= 0.65 | ~10 | **91%** | +71.5% |
| Conservador | RSI < 35 + score >= 0.75 | ~7 | **93%** | +30.5% |

## Fluxo de Treino

**Limitação:** T4 GPU tem 14.5GB VRAM. Batch size se adapta automaticamente:
- Até 15k amostras → batch 32
- 15k-25k → batch 24  
- Acima 25k → batch 16

### 1. Atualizar Dados (ocasionalmente)

Quando precisar atualizar os CSVs com dados mais recentes, rode localmente:

```powershell
.venv\Scripts\python.exe -c "
import asyncio
from src.shared.data_fetcher import DataFetcher
from src.shared.config import MAJOR_TIER_SYMBOLS, STRONG_ALT_SYMBOLS, HIGH_VOL_SYMBOLS
async def main():
    f = DataFetcher()
    for s in MAJOR_TIER_SYMBOLS + STRONG_ALT_SYMBOLS + HIGH_VOL_SYMBOLS:
        name = s.replace('/','_')
        df = await f.fetch_ohlcv(s, '15m', 6400)
        if df is not None:
            df.to_csv(f'data/raw/{name}_15m.csv', index=False)
        fr = await f.fetch_funding_rate_history(s, 1000)
        if len(fr) > 0:
            fr.to_csv(f'data/raw/{name}_funding.csv')
asyncio.run(main())
"
git add data/raw/
git commit -m "update data YYYY-MM-DD"
git push
```

### 2. Treinar os 3 modelos no Google Colab (uma célula só)

```python
%cd /content
!rm -rf fb-ml-training
!git clone https://github.com/FinBot-Crypto/fb-ml-training.git
%cd fb-ml-training
!pip install -q -r requirements.txt
!python -u _train_all.py
```

### 3. Baixar modelos treinados

```python
from google.colab import files
files.download('/content/models_mean_reversion.zip')
```

### 4. Extrair e substituir os modelos no repositorio local

```powershell
# Extrair models_mean_reversion.zip na pasta models/
# Os arquivos .pt serao:
#   model_mean_reversion_v1_lstm_Major.pt
#   model_mean_reversion_v2_lstm_StrongAlt.pt
#   model_mean_reversion_v3_lstm_HighVolatility.pt
```

## Detalhes Técnicos

**Timeframe:** 15m (96 candles/dia, 6400 candles = ~67 dias)

**Features (apenas as que importam):**
- `rsi_14` — RSI 14 períodos (14h)
- `rsi_smooth` — RSI suavizado (EMA 2)
- `rsi_14_4h` — RSI 14 em 4h (contexto multi-timeframe)

**Target:** `1 = rsi_smooth[t+48] > rsi_smooth[t]` (RSI sobe em 12h)

**Modelo:** LSTM 1 camada, 128 hidden, seq_len 144 (36h de contexto), dropout 0.2

**LOSS:** BCE (Binary Cross Entropy)

**Early stopping:** Patience 15, monitorando val_loss

**Normalização:** Z-score com stats do treino (sem data leakage)

## Pipeline de Produção

```
fb-market-selection → market.updated
  → fb-strategy-ml (carrega .pt + features → predict)
    → strategies.evaluated {score: 0.0-1.0}
      → fb-decision-engine (filtra RSI < 38 + score >= 0.65)
        → trade decision
```

## Modelos Futuros

Para replicar para V2 (Strong Alt) e V3 (High Vol):
1. Copiar estrutura: `src/models/mean_reversion_v2/`
2. Alterar `config.py`: `TIER = "Strong Alt"`
3. Gerar dados com `STRONG_ALT_SYMBOLS` ou `HIGH_VOL_SYMBOLS`
4. Treinar no Colab
5. Salvar como `model_mean_reversion_v2_lstm_StrongAlt.pt`
