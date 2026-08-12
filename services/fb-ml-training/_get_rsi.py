from binance.spot import Spot
import numpy as np
client = Spot()
klines = client.klines('ETHUSDT', '15m', limit=200)
closes = [float(k[4]) for k in klines]
delta = np.diff(closes)
gain = np.maximum(delta, 0)
loss = -np.minimum(delta, 0)
avg_gain = np.mean(gain[-56:])
avg_loss = np.mean(loss[-56:])
rsi = 100 - 100 / (1 + avg_gain / (avg_loss + 1e-10))
print(f"ETH/USDT: price={closes[-1]:.2f} RSI_56_15m={rsi:.1f}")
