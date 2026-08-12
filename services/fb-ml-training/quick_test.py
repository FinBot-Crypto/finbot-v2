"""
Script rápido para testar Mean Reversion V1 com todos os ativos do tier.
"""
import asyncio
import logging

from src.shared.logging_config import setup_logging
from src.shared.data_fetcher import BinanceDataFetcher
from src.shared.config import MAJOR_TIER_SYMBOLS
from src.models.mean_reversion_v1.evaluate import evaluate_mean_reversion_v1_tier

logger = setup_logging(level=logging.INFO)


async def quick_test():
    logger.info("="*70)
    logger.info(f"TESTE RAPIDO - Mean Reversion V1 ({MAJOR_TIER_SYMBOLS})")
    logger.info("="*70)

    logger.info("\n[1] Verificando dependencias...")
    try:
        import pandas as pd
        import sklearn
        import ccxt
        logger.info("OK - Todas as dependencias carregadas")
    except ImportError as e:
        logger.error(f"Dependencia faltando: {e}")
        return False

    logger.info(f"\n[2] Buscando dados para {MAJOR_TIER_SYMBOLS}...")
    fetcher = BinanceDataFetcher(testnet=False)

    logger.info(f"\n[3] Treinando Mean Reversion V1 (tier completo)...")
    try:
        result = await evaluate_mean_reversion_v1_tier(
            symbols=MAJOR_TIER_SYMBOLS,
            fetcher=fetcher,
        )
        logger.info("OK - Modelo treinado com sucesso!")
        logger.info(f"OK - Modelo salvo em: {result['model_path']}")

        logger.info("\n[RESULTADO FINAL]")
        logger.info(f"Train LogLoss: {result['metrics']['train']['train_logloss']:.4f} | AUC: {result['metrics']['train']['train_auc']:.4f}")
        logger.info(f"Val   LogLoss: {result['metrics']['val']['val_logloss']:.4f} | AUC: {result['metrics']['val']['val_auc']:.4f}")
        logger.info(f"Val Acc: {result['metrics']['val']['val_accuracy']:.1%}")
        logger.info(f"Proba média: {result['score_stats']['val_proba_mean']:.3f} | max: {result['score_stats']['val_proba_max']:.3f}")
        logger.info(f"LONG >= 0.75: {result['score_stats']['val_long_scores']}")
        logger.info(f"SHORT <= -0.75: {result['score_stats']['val_short_scores']}")

        return True
    except Exception as e:
        logger.error(f"Erro ao treinar: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_test())

    if success:
        logger.info("\n" + "="*70)
        logger.info("TESTE CONCLUIDO COM SUCESSO")
        logger.info("="*70)
        exit(0)
    else:
        logger.info("\n" + "="*70)
        logger.info("TESTE FALHOU")
        logger.info("="*70)
        exit(1)
