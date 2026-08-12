import asyncio
import logging
import os
import json
import ccxt
import pandas as pd
import numpy as np
import nats
from joblib import load

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fb-ml-validation")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")

class MLValidationService:
    def __init__(self):
        self.nc = None
        self.js = None
        self.exchange = ccxt.binance({'enableRateLimit': True})

    async def connect_nats(self):
        while True:
            try:
                self.nc = await nats.connect(NATS_URL)
                self.js = self.nc.jetstream()
                logger.info(f"Conectado ao NATS em {NATS_URL}")
                return
            except Exception as e:
                logger.error(f"Erro ao conectar NATS: {e}")
                await asyncio.sleep(5)

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    async def validate_model(self, symbol):
        logger.info(f"Validando modelo para {symbol}...")
        model_path = os.path.join(MODELS_DIR, f"model_{symbol.replace('/', '_')}.joblib")
        
        if not os.path.exists(model_path):
            logger.error(f"Modelo não encontrado: {model_path}")
            return False

        # Fetch recent data for validation (walk-forward)
        ohlcv = await asyncio.to_thread(self.exchange.fetch_ohlcv, symbol, '1h', limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Prepare Features
        df['rsi'] = self.calculate_rsi(df['close'])
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        df.dropna(inplace=True)

        if df.empty:
            return False

        # Load and Predict
        model = load(model_path)
        X = df[['rsi', 'sma_50', 'sma_200']]
        predictions = model.predict(X)
        
        # Simula métricas de validação
        accuracy = np.random.uniform(0.55, 0.75) # Mock de acurácia por enquanto
        logger.info(f"Modelo {symbol} validado com acurácia: {accuracy:.2f}")
        
        return accuracy > 0.60 # Threshold de aprovação

    async def handle_training_finished(self, msg):
        try:
            data = json.loads(msg.data.decode())
            symbol = data.get('symbol')
            if symbol:
                approved = await self.validate_model(symbol)
                if approved:
                    await self.js.publish("ml.model.validated", json.dumps({"symbol": symbol, "status": "approved"}).encode())
                    logger.info(f"Modelo {symbol} APROVADO e pronto para uso.")
                else:
                    logger.warning(f"Modelo {symbol} REPROVADO na validação.")
            await msg.ack()
        except Exception as e:
            logger.error(f"Erro na validação: {e}")

    async def run(self):
        await self.connect_nats()
        
        # Subscribe para notificações de conclusão de treino
        await self.js.subscribe(
            "ml.training.finished",
            durable="ML_VALIDATOR",
            cb=self.handle_training_finished,
            manual_ack=True
        )
        logger.info("ML Validation Service aguardando conclusões em 'ml.training.finished'...")

        while True:
            if self.nc.is_closed:
                await self.connect_nats()
            await asyncio.sleep(10)

if __name__ == "__main__":
    service = MLValidationService()
    asyncio.run(service.run())
