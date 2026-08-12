# Mean Reversion Models - Resultados e Thresholds

## Modelos Treinados (3 tiers, 19 ativos)

| Tier | Ativos | AUC Val | Sinais/dia | WR | Threshold |
|------|--------|---------|-----------|-----|-----------|
| **V1 Major** | BTC, ETH | 0.836 | ~2/dia | **86.8%** | RSI<38 + score>=0.65 |
| **V2 Strong Alt** | SOL, MATIC, AVAX, LINK, DOGE, ADA, XRP | 0.819 | ~15/dia | **86.8%** | RSI<38 + score>=0.65 |
| **V3 High Vol** | ARB, OP, LDO, ATOM, NEAR, INJ, PEPE, SHIB, MEME, GALA | 0.820 | ~10/dia | **61.7%*** | RSI<38 + score>=0.65 |

*V3 WR varia por símbolo: PEPE 100%, SHIB 93%, MEME 89%, OP 86%, GALA 86%, INJ 84%, mas LDO 46% e NEAR 12% puxam pra baixo.

## Arquitetura do Modelo

- **Arquitetura:** LSTM 1 camada, 128 hidden, seq_len 144 (36h)
- **Target:** RSI[t+48] > RSI[t] (direção do RSI em 12h)
- **Features:** rsi_14, rsi_smooth, rsi_14_4h
- **Timeframe:** 15m
- **Dados:** 6400 candles (~67 dias) por ativo
- **Normalização:** Z-score com stats do treino (sem data leakage)
- **Loss:** Binary Cross Entropy
- **Early stopping:** Patience 15

## Como Usar em Produção

O modelo é carregado pelo `fb-strategy-ml` que:
1. Busca dados OHLCV recentes do ativo
2. Calcula as 3 features RSI
3. Faz `model.predict_proba(features)` → score 0-1
4. Se RSI < 38 E score >= 0.65 → sinal LONG
5. Publica em `strategies.evaluated` com score e confiança

## Model Files

- `models/model_mean_reversion_v1_lstm_Major.pt`
- `models/model_mean_reversion_v1_lstm_StrongAlt.pt`
- `models/model_mean_reversion_v1_lstm_HighVolatility.pt`

## Simulação (TP 2.5% / SL 2%, 12h hold)

**V1 (BTC+ETH):**
- Dia 2 BTC: 8 trades, 8W/0L, +20%
- Dia 2 ETH: 10 trades, 8W/1L, +17.2%

**V2 (7 ativos):**
- Dia 1: 78 trades, 78W/0L, +195%
- Dia 2: 162 trades, 119W/48L, +201%  
- Dia 6: 147 trades, 68W/19L, +132%

**V3 (10 ativos):**
- WR por símbolo: PEPE 100%, SHIB 93%, INJ 84%, GALA 86%, OP 86%, MEME 89%
- LDO (46%) e NEAR (12%) com baixa performance
