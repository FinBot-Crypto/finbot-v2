"""
Treino + Analise de features em sequencia.
Mostra epoca a epoca + permutation importance ao final.
"""
import asyncio, sys, logging, numpy as np, pandas as pd, torch
sys.path.insert(0, r'C:\Users\Renan\PythonProjects\financas_crypto_bot\services\fb-ml-training')

from src.shared.logging_config import setup_logging
from src.shared.data_fetcher import DataFetcher
from src.shared.config import MODELS_DIR
from src.shared.config import TIER_SYMBOLS
from src.models.mean_reversion_v1.dataset import MeanReversionV1Dataset
from src.models.mean_reversion_v1.lstm_train import MeanReversionV1LSTMTrainer, make_sequences
from src.models.mean_reversion_v1 import config
from sklearn.metrics import roc_auc_score

logger = setup_logging(level=logging.INFO)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


async def main():
    fetcher = DataFetcher()
    all_X_tr, all_X_va = [], []
    all_y_tr, all_y_va = [], []

    symbols = TIER_SYMBOLS.get(config.TIER, [])
    if not symbols:
        logger.error(f"Tier {config.TIER} sem simbolos definidos")
        return
    for symbol in symbols:
        logger.info(f"Buscando {symbol}...")
        df = await fetcher.fetch_ohlcv(symbol, config.TIMEFRAME, config.CANDLES_TO_FETCH)
        if df is None: continue
        # Buscar dados de futures
        fr = await fetcher.fetch_funding_rate_history(symbol, 1000)
        oi = await fetcher.fetch_open_interest_history(symbol, 1000)
        ds = MeanReversionV1Dataset(symbol=symbol).set_futures_data(funding_df=fr, oi_df=oi)
        X_tr, X_va, y_tr, y_va = ds.prepare(df)
        all_X_tr.append(X_tr); all_y_tr.append(y_tr)
        all_X_va.append(X_va); all_y_va.append(y_va)

    X_train = pd.concat(all_X_tr).reset_index(drop=True)
    X_val = pd.concat(all_X_va).reset_index(drop=True)
    y_train = pd.concat(all_y_tr).reset_index(drop=True)
    y_val = pd.concat(all_y_va).reset_index(drop=True)

    logger.info(f"\nDataset: {X_train.shape[0]} train, {X_val.shape[0]} val, {X_train.shape[1]} features")
    sys.stdout.flush()

    # Treino (mostra epoca a epoca)
    trainer = MeanReversionV1LSTMTrainer(models_dir=MODELS_DIR)
    metrics = trainer.train(X_train, y_train, X_val, y_val)
    sys.stdout.flush()

    # Baseline AUC
    seq_len = config.SEQ_LEN
    Xs_va, ys_va = make_sequences(X_val, y_val, seq_len)
    with torch.no_grad():
        proba = trainer.model(torch.from_numpy(Xs_va).to(device)).cpu().numpy().flatten()
    baseline = roc_auc_score(ys_va, proba)

    # Permutation importance
    print(f"\n{'='*70}")
    print(f"PERMUTATION IMPORTANCE - {X_train.shape[1]} features")
    print(f"Baseline AUC: {baseline:.4f}")
    print(f"{'='*70}")
    print(f"{'Feature':<25} {'AUC c/ shuffle':<15} {'Queda':<10} {'Impacto'}")
    print(f"{'-'*70}")
    sys.stdout.flush()

    results = []
    for i, col in enumerate(X_train.columns):
        X_val_shuffled = X_val.copy()
        np.random.seed(42)
        X_val_shuffled[col] = np.random.permutation(X_val_shuffled[col].values)

        Xs_shuf, _ = make_sequences(X_val_shuffled, y_val, seq_len)
        with torch.no_grad():
            p_shuf = trainer.model(torch.from_numpy(Xs_shuf).to(device)).cpu().numpy().flatten()
        auc_shuf = roc_auc_score(ys_va, p_shuf)
        drop = baseline - auc_shuf

        if drop > 0.01:    impact = "POSITIVO"
        elif drop < -0.01: impact = "NEGATIVO"
        else:              impact = "NEUTRO"
        results.append((col, auc_shuf, drop, impact))

    results.sort(key=lambda x: x[2], reverse=True)
    for col, auc_s, drop, imp in results:
        print(f"{col:<25} {auc_s:<15.4f} {drop:<10.4f} {imp}")
    sys.stdout.flush()

    print(f"\nFeatures POSITIVAS:")
    for col, auc_s, drop, imp in results:
        if imp == "POSITIVO": print(f"  + {col}")
    print(f"\nFeatures NEUTRAS:")
    for col, auc_s, drop, imp in results:
        if imp == "NEUTRO": print(f"  ~ {col}")
    print(f"\nFeatures NEGATIVAS:")
    for col, auc_s, drop, imp in results:
        if imp == "NEGATIVO": print(f"  - {col}")
    sys.stdout.flush()

    model_path = trainer.save_model("Major")
    logger.info(f"Modelo salvo: {model_path}")

asyncio.run(main())

