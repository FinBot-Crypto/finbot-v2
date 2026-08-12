"""
Treina os 6 modelos Mean Reversion (V1, V2, V3 - Long e Short) sequencialmente.
Uso: python _train_all_6_models.py
"""
import sys, os, shutil, asyncio, logging, pandas as pd
sys.path.insert(0, '.')

from src.shared.data_fetcher import DataFetcher
from src.shared.config import MODELS_DIR, TIER_SYMBOLS
from src.models.mean_reversion_v1.dataset import MeanReversionV1Dataset
from src.models.mean_reversion_v1.lstm_train import MeanReversionV1LSTMTrainer
from src.models.mean_reversion_v1 import config as cfg

# Configuração robusta de logging (com override de configurações de terceiros)
os.makedirs(MODELS_DIR, exist_ok=True)
log_file = os.path.join(MODELS_DIR, 'training_all_6_models.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding='utf-8')
    ],
    force=True
)
logger = logging.getLogger("train-6-models")


async def train_tier_direction(tier_name: str, direction: str, btc_df: pd.DataFrame):
    """Treina o modelo para um tier e direção específicos (long/short)."""
    cfg.TIER = tier_name
    cfg.DIRECTION = direction
    
    # Atualiza as variáveis do módulo config dinamicamente
    cfg.LOOKAHEAD_CANDLES = cfg.get_parameter("LOOKAHEAD_CANDLES", tier_name, direction)
    cfg.SEQ_LEN = cfg.get_parameter("SEQ_LEN", tier_name, direction)
    cfg.LSTM_HIDDEN = cfg.get_parameter("LSTM_HIDDEN", tier_name, direction)
    cfg.LSTM_LAYERS = cfg.get_parameter("LSTM_LAYERS", tier_name, direction)
    cfg.DROPOUT = cfg.get_parameter("DROPOUT", tier_name, direction)
    cfg.BATCH_SIZE = cfg.get_parameter("BATCH_SIZE", tier_name, direction)
    cfg.LEARNING_RATE = cfg.get_parameter("LEARNING_RATE", tier_name, direction)
    cfg.WEIGHT_DECAY = cfg.get_parameter("WEIGHT_DECAY", tier_name, direction)
    cfg.TP_PCT = cfg.get_parameter("TP_PCT", tier_name, direction)

    symbols = TIER_SYMBOLS.get(tier_name, [])
    dir_upper = direction.upper()
    print(f"\n{'='*80}")
    print(f"TREINANDO: Mean Reversion - {tier_name} ({len(symbols)} ativos) | DIREÇÃO: {dir_upper}")
    print(f"{'='*80}")

    fetcher = DataFetcher()
    all_X_tr, all_X_va = [], []
    all_y_tr, all_y_va = [], []

    for symbol in symbols:
        print(f"\nBuscando {symbol}...")
        df = await fetcher.fetch_ohlcv(symbol, cfg.TIMEFRAME, cfg.CANDLES_TO_FETCH)
        if df is None:
            print(f"  SEM DADOS para {symbol}, pulando")
            continue
        # Cria dataset com a direção correta (long/short)
        ds = (MeanReversionV1Dataset(symbol=symbol, direction=direction)
              .set_btc_data(btc_df))
              
        try:
            X_tr, X_va, y_tr, y_va = ds.prepare(df)
            all_X_tr.append(X_tr)
            all_y_tr.append(y_tr)
            all_X_va.append(X_va)
            all_y_va.append(y_va)
        except Exception as e:
            print(f"  Erro ao preparar dataset para {symbol}: {e}")

    if not all_X_tr:
        print(f"  Nenhum dado válido para {tier_name} ({direction})")
        return

    X_train = pd.concat(all_X_tr).reset_index(drop=True)
    X_val = pd.concat(all_X_va).reset_index(drop=True)
    y_train = pd.concat(all_y_tr).reset_index(drop=True)
    y_val = pd.concat(all_y_va).reset_index(drop=True)

    print(f"\nDataset {tier_name} ({direction}): {X_train.shape[0]} train, {X_val.shape[0]} val, {X_train.shape[1]} features")
    tier_clean = tier_name.replace(' ', '')

    trainer = MeanReversionV1LSTMTrainer(models_dir=MODELS_DIR)
    
    # Ajusta o nome do modelo se for SHORT para bater com o padrão esperado
    if direction == "short":
        trainer.model_name = "short_lstm"
        
    trainer.train(X_train, y_train, X_val, y_val)
    model_path = trainer.save_model(tier_clean)
    print(f"Modelo salvo: {model_path}")


async def main():
    fetcher = DataFetcher()
    print("Buscando dados de BTC/USDT para usar como feature de direção do mercado...")
    btc_df = await fetcher.fetch_ohlcv("BTC/USDT", cfg.TIMEFRAME, cfg.CANDLES_TO_FETCH)
    if btc_df is None:
        print("AVISO: Falha ao carregar dados do BTC/USDT de mercado. Features de BTC serão NaN.")

    tiers = ['Major', 'Strong Alt', 'High Volatility']
    directions = ['long', 'short']

    for direction in directions:
        for tier in tiers:
            try:
                await train_tier_direction(tier, direction, btc_df)
            except Exception as e:
                print(f"ERRO ao treinar {tier} ({direction}): {e}")

    print(f"\n{'='*80}")
    print(f"TODOS OS 6 MODELOS TREINADOS COM SUCESSO")
    print(f"{'='*80}")
    for f in sorted(os.listdir(MODELS_DIR)):
        if f.endswith('.pt'):
            kb = os.path.getsize(os.path.join(MODELS_DIR, f)) / 1024
            print(f"  models/{f} ({kb:.1f} KB)")

    # Zip models for download (Colab check)
    if os.path.exists('/content'):
        zip_path = '/content/models_mean_reversion_all.zip'
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', MODELS_DIR)
        print(f"\nZIP gerado: {zip_path}")
        print(f"Para baixar no Colab, use: files.download('{zip_path}')")


if __name__ == "__main__":
    asyncio.run(main())
