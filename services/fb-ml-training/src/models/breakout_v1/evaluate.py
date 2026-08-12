"""
Script de avaliação para modelo Breakout V1.
"""
import logging
import pandas as pd
import json
from datetime import datetime, timezone
from src.models.breakout_v1.dataset import BreakoutV1Dataset
from src.models.breakout_v1.train import BreakoutV1Trainer
from src.shared.config import MODELS_DIR, PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def evaluate_breakout_v1(symbol: str, df: pd.DataFrame) -> dict:
    """
    Treina e avalia modelo Breakout V1 para um símbolo.
    
    Args:
        symbol: Par de trading (ex: BTC/USDT)
        df: DataFrame com OHLCV
    
    Returns:
        Dict com resultado da avaliação
    """
    logger.info(f"{'='*60}")
    logger.info(f"AVALIANDO: Breakout V1 - {symbol}")
    logger.info(f"{'='*60}")
    
    # 1. Criar dataset
    dataset = BreakoutV1Dataset(symbol=symbol)
    X_train, X_val, y_train, y_val = dataset.prepare(df)
    
    logger.info(f"\n[1] Dataset criado:")
    logger.info(f"    X_train: {X_train.shape}")
    logger.info(f"    X_val: {X_val.shape}")
    logger.info(f"    Features: {list(X_train.columns)}")
    
    # 2. Treinar modelo
    trainer = BreakoutV1Trainer(models_dir=MODELS_DIR)
    train_metrics = trainer.train(X_train, y_train)
    
    logger.info(f"\n[2] Modelo treinado")
    
    # 3. Avaliar
    val_metrics = trainer.evaluate(X_val, y_val)
    
    logger.info(f"\n[3] Modelo avaliado")
    
    # 4. Salvar modelo
    model_path = trainer.save_model(symbol)
    
    logger.info(f"\n[4] Modelo salvo em: {model_path}")
    
    # 5. Feature importance
    try:
        importance = trainer.get_feature_importance(top_n=8)
        logger.info(f"\n[5] Feature Importance (Top 8):")
        logger.info(importance)
    except:
        importance = None
    
    # 6. Compilar resultado
    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'model': 'breakout_v1',
        'symbol': symbol,
        'model_path': model_path,
        'dataset_info': {
            'train_size': len(X_train),
            'val_size': len(X_val),
            'n_features': X_train.shape[1],
            'features': list(X_train.columns)
        },
        'metrics': {
            'train': train_metrics,
            'val': val_metrics
        }
    }
    
    logger.info(f"\n[RESULTADO FINAL]")
    logger.info(f"Treino: {train_metrics}")
    logger.info(f"Validação: {val_metrics}")
    
    return result


if __name__ == "__main__":
    """
    Script principal - executa avaliação completa.
    """
    import asyncio
    from src.shared.data_fetcher import BinanceDataFetcher
    
    async def main():
        # Símbolos para testar (Major tier)
        symbols = ["BTC/USDT", "ETH/USDT"]
        
        # Inicializar fetcher
        fetcher = BinanceDataFetcher(testnet=False)
        
        results = []
        for symbol in symbols:
            logger.info(f"\n{'='*60}\nBuscando dados para {symbol}...\n")
            
            # Buscar dados
            df = await fetcher.fetch_ohlcv(symbol, timeframe="1h", limit=1000)
            
            if df is None or len(df) < 300:
                logger.error(f"✗ Dados insuficientes para {symbol}")
                continue
            
            # Avaliar
            result = evaluate_breakout_v1(symbol, df)
            results.append(result)
        
        # Salvar resultados
        logger.info(f"\n{'='*60}\n[RESUMO FINAL]\n{'='*60}")
        
        for result in results:
            logger.info(f"\n{result['symbol']}:")
            logger.info(f"  Train Accuracy: {result['metrics']['train']['train_accuracy']:.4f}")
            logger.info(f"  Val Accuracy: {result['metrics']['val']['val_accuracy']:.4f}")
            logger.info(f"  Val F1: {result['metrics']['val']['val_f1']:.4f}")
            logger.info(f"  Val AUC: {result['metrics']['val']['val_auc']:.4f}")
        
        # Salvar JSON com resultados
        import json
        results_path = f"{PROCESSED_DATA_DIR}/breakout_v1_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\n✓ Resultados salvos em: {results_path}")
    
    asyncio.run(main())
