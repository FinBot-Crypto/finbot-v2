"""
Script de avaliação para Mean Reversion V1 (XGBoost Regressor).

Treina um ÚNICO modelo por tier com dados de TODOS os ativos do tier.
Ex: Mean Reversion V1 (Major) treinado com BTC + USDT.
"""
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from src.models.mean_reversion_v1.dataset import MeanReversionV1Dataset
from src.models.mean_reversion_v1.train import MeanReversionV1Trainer
from src.models.mean_reversion_v1 import config
from src.shared.config import MODELS_DIR, PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def evaluate_mean_reversion_v1_tier(
    symbols: list,
    fetcher
) -> dict:
    """
    Treina e avalia Mean Reversion V1 com dados de todos os símbolos do tier.
    """
    tier_name = config.TIER
    logger.info(f"{'='*60}")
    logger.info(f"TREINANDO: Mean Reversion V1 - {tier_name}")
    logger.info(f"  Ativos: {symbols}")
    logger.info(f"{'='*60}")

    all_X_train, all_X_val = [], []
    all_y_train, all_y_val = [], []

    for symbol in symbols:
        logger.info(f"\n--- Processando {symbol} ---")
        df = await fetcher.fetch_ohlcv(symbol, timeframe=config.TIMEFRAME, limit=config.CANDLES_TO_FETCH)
        if df is None or len(df) < 300:
            logger.warning(f"Dados insuficientes para {symbol}, pulando")
            continue

        dataset = MeanReversionV1Dataset(symbol=symbol)
        X_train, X_val, y_train, y_val = dataset.prepare(df)

        logger.info(f"  {symbol}: {len(X_train)} train, {len(X_val)} val")

        all_X_train.append(X_train)
        all_X_val.append(X_val)
        all_y_train.append(y_train)
        all_y_val.append(y_val)

    X_train = pd.concat(all_X_train).reset_index(drop=True)
    X_val = pd.concat(all_X_val).reset_index(drop=True)
    y_train = pd.concat(all_y_train).reset_index(drop=True)
    y_val = pd.concat(all_y_val).reset_index(drop=True)

    logger.info(f"\n[1] Dataset total do tier {tier_name}:")
    logger.info(f"    X_train: {X_train.shape} | X_val: {X_val.shape}")
    logger.info(f"    y_train: média={y_train.mean():.4f} std={y_train.std():.4f}")
    logger.info(f"    y_val:   média={y_val.mean():.4f} std={y_val.std():.4f}")

    trainer = MeanReversionV1Trainer(models_dir=MODELS_DIR)
    logger.info(f"\n[2] Treinando XGBoost...")
    train_metrics = trainer.train(X_train, y_train, X_val, y_val)

    logger.info(f"\n[3] Validando...")
    val_metrics = trainer.evaluate(X_val, y_val)

    model_path = trainer.save_model(tier_name)
    logger.info(f"\n[4] Modelo salvo: {model_path}")

    try:
        importance = trainer.get_feature_importance(top_n=8)
        logger.info(f"\n[5] Feature Importance (Top 8):")
        logger.info(importance.to_string(index=False))
    except:
        importance = None

    val_proba = trainer.model.predict_proba(X_val)[:, 1]
    val_score = 2 * val_proba - 1  # proba [0,1] → score [-1,+1]

    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'model': 'mean_reversion_v1',
        'tier': tier_name,
        'symbols': symbols,
        'model_path': model_path,
        'dataset_info': {
            'train_size': len(X_train),
            'val_size': len(X_val),
            'n_features': X_train.shape[1],
            'features': list(X_train.columns),
        },
        'metrics': {
            'train': train_metrics,
            'val': val_metrics,
        },
        'score_stats': {
            'val_score_mean': float(val_score.mean()),
            'val_score_std': float(val_score.std()),
            'val_long_scores': int((val_score >= 0.75).sum()),
            'val_short_scores': int((val_score <= -0.75).sum()),
            'val_proba_mean': float(val_proba.mean()),
            'val_proba_max': float(val_proba.max()),
        },
    }

    logger.info(f"\n{'='*60}")
    logger.info(f"[RESUMO] Mean Reversion V1 - {tier_name}")
    logger.info(f"  Train LogLoss: {train_metrics['train_logloss']:.4f} | AUC: {train_metrics['train_auc']:.4f}")
    logger.info(f"  Val   LogLoss: {val_metrics['val_logloss']:.4f} | AUC: {val_metrics['val_auc']:.4f}")
    logger.info(f"  Val Acc: {val_metrics['val_accuracy']:.1%}")
    logger.info(f"  Proba média: {result['score_stats']['val_proba_mean']:.3f} | max: {result['score_stats']['val_proba_max']:.3f}")
    logger.info(f"  LONG >= 0.75: {result['score_stats']['val_long_scores']}")
    logger.info(f"  SHORT <= -0.75: {result['score_stats']['val_short_scores']}")
    logger.info(f"{'='*60}")

    return result


if __name__ == "__main__":
    import asyncio
    from src.shared.data_fetcher import BinanceDataFetcher
    from src.shared.config import MAJOR_TIER_SYMBOLS

    async def main():
        fetcher = BinanceDataFetcher(testnet=False)
        symbols = MAJOR_TIER_SYMBOLS

        result = await evaluate_mean_reversion_v1_tier(
            symbols=symbols,
            fetcher=fetcher,
        )

        results_path = f"{PROCESSED_DATA_DIR}/mean_reversion_v1_results.json"
        with open(results_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"\nResultados salvos em: {results_path}")

    asyncio.run(main())