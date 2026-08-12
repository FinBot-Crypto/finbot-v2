"""
Permutation Importance para LSTM.
Embaralha cada feature e mede queda de AUC.
"""
import asyncio, sys, numpy as np, pandas as pd
sys.path.insert(0, '.')

from src.shared.data_fetcher import DataFetcher
from src.shared.config import MAJOR_TIER_SYMBOLS, MODELS_DIR
from src.models.mean_reversion_v1.dataset import MeanReversionV1Dataset
from src.models.mean_reversion_v1.lstm_train import MeanReversionV1LSTMTrainer, make_sequences
from src.models.mean_reversion_v1 import config
from sklearn.metrics import roc_auc_score
import torch

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Treina modelo
async def train():
    f = DataFetcher()
    print("Buscando dados do BTC/USDT...")
    btc_df = await f.fetch_ohlcv("BTC/USDT", config.TIMEFRAME, config.CANDLES_TO_FETCH)
    if btc_df is None:
        print("Falha ao carregar dados do BTC/USDT.")
        return
        
    X_tr, X_va, y_tr, y_va = [], [], [], []
    for s in MAJOR_TIER_SYMBOLS:
        df = await f.fetch_ohlcv(s, config.TIMEFRAME, config.CANDLES_TO_FETCH)
        if df is None: continue
        fr = await f.fetch_funding_rate_history(s, 1000)
        oi = await f.fetch_open_interest_history(s, 1000)
        ds = (MeanReversionV1Dataset(symbol=s)
              .set_futures_data(funding_df=fr, oi_df=oi)
              .set_btc_data(btc_df))
        a,b,c,d = ds.prepare(df)
        X_tr.append(a); X_va.append(b); y_tr.append(c); y_va.append(d)
    X_train = pd.concat(X_tr).reset_index(drop=True)
    X_val = pd.concat(X_va).reset_index(drop=True)
    y_train = pd.concat(y_tr).reset_index(drop=True)
    y_val = pd.concat(y_va).reset_index(drop=True)
    
    trainer = MeanReversionV1LSTMTrainer(models_dir=MODELS_DIR)
    trainer.train(X_train, y_train, X_val, y_val)
    
    # Baseline AUC
    seq_len = config.SEQ_LEN
    Xs_va, ys_va = make_sequences(X_val, y_val, seq_len)
    with torch.no_grad():
        proba = trainer.model(torch.from_numpy(Xs_va).to(device)).cpu().numpy().flatten()
    baseline = roc_auc_score(ys_va, proba)
    
    print(f"\n{'='*70}")
    print(f"PERMUTATION IMPORTANCE - {X_train.shape[1]} features")
    print(f"Baseline AUC: {baseline:.4f}")
    print(f"{'='*70}")
    print(f"{'Feature':<25} {'AUC c/ shuffle':<15} {'Queda':<10} {'Impacto'}")
    print(f"{'-'*70}")
    
    results = []
    for i, col in enumerate(X_train.columns):
        X_val_shuffled = X_val.copy()
        X_val_shuffled[col] = np.random.permutation(X_val_shuffled[col].values)
        
        Xs_shuf, ys_shuf = make_sequences(X_val_shuffled, y_val, seq_len)
        with torch.no_grad():
            p_shuf = trainer.model(torch.from_numpy(Xs_shuf).to(device)).cpu().numpy().flatten()
        auc_shuf = roc_auc_score(ys_shuf, p_shuf)
        drop = baseline - auc_shuf
        
        if drop > 0.01: impact = "POSITIVO"
        elif drop < -0.01: impact = "NEGATIVO"
        else: impact = "NEUTRO"
        
        results.append((col, auc_shuf, drop, impact))
    
    results.sort(key=lambda x: x[2], reverse=True)
    for col, auc_s, drop, imp in results:
        print(f"{col:<25} {auc_s:<15.4f} {drop:<10.4f} {imp}")
    
    print(f"\nFeatures POSITIVAS (embaralhar piorou o modelo):")
    for col, auc_s, drop, imp in results:
        if imp == "POSITIVO": print(f"  + {col} (queda de {drop:.4f})")
    
    print(f"\nFeatures NEUTRAS (sem impacto):")
    for col, auc_s, drop, imp in results:
        if imp == "NEUTRO": print(f"  ~ {col}")

asyncio.run(train())
