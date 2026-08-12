"""
Treina os 3 modelos Mean Reversion (V1, V2, V3) sequencialmente.
Uso no Colab: python _train_all.py
"""
import sys, os, shutil, asyncio, logging, pandas as pd
sys.path.insert(0, '.')

logging.basicConfig(level=logging.INFO, format='%(message)s')

from src.shared.data_fetcher import DataFetcher
from src.shared.config import MODELS_DIR
from src.shared.config import TIER_SYMBOLS
from src.models.mean_reversion_v1.dataset import MeanReversionV1Dataset
from src.models.mean_reversion_v1.lstm_train import MeanReversionV1LSTMTrainer
from src.models.mean_reversion_v1 import config as cfg


async def train_tier(tier_name: str):
    """Treina modelo para um tier especifico."""
    cfg.TIER = tier_name
    symbols = TIER_SYMBOLS.get(tier_name, [])
    print(f"\n{'='*70}")
    print(f"TREINANDO: Mean Reversion - {tier_name} ({len(symbols)} ativos)")
    print(f"{'='*70}")

    fetcher = DataFetcher()
    all_X_tr, all_X_va = [], []
    all_y_tr, all_y_va = [], []

    for symbol in symbols:
        print(f"\nBuscando {symbol}...")
        df = await fetcher.fetch_ohlcv(symbol, cfg.TIMEFRAME, cfg.CANDLES_TO_FETCH)
        if df is None:
            print(f"  SEM DADOS para {symbol}, pulando")
            continue
        fr = await fetcher.fetch_funding_rate_history(symbol, 1000)
        ds = MeanReversionV1Dataset(symbol=symbol).set_futures_data(funding_df=fr)
        X_tr, X_va, y_tr, y_va = ds.prepare(df)
        all_X_tr.append(X_tr); all_y_tr.append(y_tr)
        all_X_va.append(X_va); all_y_va.append(y_va)

    if not all_X_tr:
        print(f"  Nenhum dado para {tier_name}")
        return

    X_train = pd.concat(all_X_tr).reset_index(drop=True)
    X_val = pd.concat(all_X_va).reset_index(drop=True)
    y_train = pd.concat(all_y_tr).reset_index(drop=True)
    y_val = pd.concat(all_y_va).reset_index(drop=True)

    print(f"\nDataset: {X_train.shape[0]} train, {X_val.shape[0]} val, {X_train.shape[1]} features")
    tier_clean = tier_name.replace(' ', '')

    trainer = MeanReversionV1LSTMTrainer(models_dir=MODELS_DIR)
    trainer.train(X_train, y_train, X_val, y_val)
    model_path = trainer.save_model(tier_clean)
    print(f"Modelo salvo: {model_path}")


async def main():
    tiers = ['Major', 'Strong Alt', 'High Volatility']
    for tier in tiers:
        await train_tier(tier)

    print(f"\n{'='*70}")
    print(f"TODOS OS MODELOS TREINADOS")
    print(f"{'='*70}")
    for f in os.listdir(MODELS_DIR):
        if f.endswith('.pt'):
            print(f"  models/{f}")

    # Zip models for download
    zip_path = '/content/models_mean_reversion.zip'
    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', MODELS_DIR)
    print(f"\nZIP: {zip_path}")
    print(f"Comando para baixar: files.download('{zip_path}')")

asyncio.run(main())
