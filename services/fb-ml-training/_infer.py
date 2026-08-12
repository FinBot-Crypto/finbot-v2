"""
Inferencia LSTM: carrega modelo, busca dados recentes, mostra sinais.
Traducao: score = proba do RSI subir. LONG se score > 0.75 + RSI baixo.
"""
import sys, asyncio, logging, numpy as np, pandas as pd, torch
sys.path.insert(0, r'C:\Users\Renan\PythonProjects\financas_crypto_bot\services\fb-ml-training')

from src.shared.data_fetcher import DataFetcher
from src.shared.config import MAJOR_TIER_SYMBOLS
from src.shared.indicators import calculate_rsi
from src.models.mean_reversion_v1.dataset import MeanReversionV1Dataset
from src.models.mean_reversion_v1.lstm_train import LSTMMeanReversion, make_sequences
from src.models.mean_reversion_v1 import config

logging.basicConfig(level=logging.WARNING)
device = torch.device('cpu')
model_path = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\Renan\Downloads\model_mean_reversion_v1_lstm_Major.pt'

# Carrega modelo
ckpt = torch.load(model_path, map_location=device, weights_only=False)
cfg = ckpt.get('config', {})
feature_names = ckpt.get('feature_names', config.FEATURES)
model = LSTMMeanReversion(
    input_size=len(feature_names),
    hidden_size=cfg.get('hidden', 128),
    num_layers=cfg.get('layers', 1),
    dropout=0
).to(device)
model.load_state_dict(ckpt['model_state_dict'])
model.eval()

SL_PCT, TP_PCT = 0.02, 0.06

async def main():
    f = DataFetcher()
    all_rows = []

    # Busca dados do BTC/USDT para usar como feature
    btc_df = await f.fetch_ohlcv("BTC/USDT", config.TIMEFRAME, config.CANDLES_TO_FETCH)

    for symbol in MAJOR_TIER_SYMBOLS:
        df = await f.fetch_ohlcv(symbol, config.TIMEFRAME, config.CANDLES_TO_FETCH)
        if df is None: continue
        fr = await f.fetch_funding_rate_history(symbol, 1000)
        oi = await f.fetch_open_interest_history(symbol, 1000)
        ds = MeanReversionV1Dataset(symbol=symbol).set_futures_data(funding_df=fr, oi_df=oi).set_btc_data(btc_df)
        X, y = ds.prepare(df)[1], ds.prepare(df)[3]
        X = X[feature_names]
        # RSI raw (nao normalizado) direto do OHLCV
        rsi_period = 56 if config.TIMEFRAME == '15m' else 14
        rsi_raw = calculate_rsi(df['close'], rsi_period)
        seq_len = cfg.get('seq_len', 96)
        if len(X) < seq_len: continue
        Xs, ys = make_sequences(X, y, seq_len)
        with torch.no_grad():
            proba = model(torch.from_numpy(Xs).to(device)).numpy().flatten()
        # Ultimos 48 candles (12h)
        for i in range(max(0, len(proba)-48), len(proba)):
            idx = i + seq_len
            all_rows.append({
                'symbol': symbol,
                'proba': float(proba[i]),
                'rsi': float(rsi_raw.iloc[idx]) if idx < len(rsi_raw) else 50,
                'target': int(ys[i]),
            })

    if not all_rows:
        print("Sem dados")
        return

    df_r = pd.DataFrame(all_rows)
    df_r['score'] = df_r['proba']
    df_r['rsi'] = df_r['rsi']

    print(f"\n{'='*70}")
    print(f"RELATORIO DE INFERENCIA - {len(df_r)} candles recentes")
    print(f"{'='*70}")

    # Sinais LONG: score > threshold E RSI baixo (sobre-venda)
    for thresh in [0.75, 0.7, 0.6]:
        long = df_r[(df_r['score'] >= thresh) & (df_r['rsi'] < 45)]
        long_ok = long[long['target'] == 1]  # target=1 significa RSI subiu
        long_ko = long[long['target'] == 0]
        n = len(long)
        wr = len(long_ok) / n if n > 0 else 0
        print(f"\nLONG (score>={thresh}, RSI<45):")
        print(f"  {n} sinais | {len(long_ok)} acertos | {len(long_ko)} erros | WR={wr:.0%}")
        if n > 0:
            exp_ret = wr * TP_PCT - (1-wr) * SL_PCT
            print(f"  Retorno esperado/trade: {exp_ret:.2%} | Lucro total: R${10000 * (1+exp_ret*n):.0f}")

    print(f"\nScore stats: media={df_r['score'].mean():.3f} std={df_r['score'].std():.3f}")
    print(f"RSI medio: {df_r['rsi'].mean():.1f}")

    print(f"\nUltimos 12 candles:")
    for _, r in df_r.tail(12).iterrows():
        long = 'LONG' if r['score'] > 0.6 and r['rsi'] < 45 else ('SHORT' if r['score'] < 0.4 and r['rsi'] > 55 else '--')
        ok = '+' if (r['score'] > 0.5 and r['target'] == 1) or (r['score'] < 0.5 and r['target'] == 0) else '-'
        print(f"  {r['symbol']:<10} score={r['score']:.3f} rsi={r['rsi']:.1f} {long:<6} target={'SOBE' if r['target'] else 'DESCE'} {ok}")

asyncio.run(main())
