"""Teste end-to-end: fetch dados, features, modelo -> score."""
import numpy as np, pandas as pd, torch, torch.nn as nn, ccxt

class LSTMMeanReversion(nn.Module):
    def __init__(self, input_size=3, hidden_size=128, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return torch.sigmoid(self.fc(lstm_out[:, -1, :]))

exchange = ccxt.binance({'enableRateLimit': True})
TIERS = {'Major': ['BTC/USDT','ETH/USDT'], 'Strong Alt': ['SOL/USDT','DOGE/USDT'], 'High Volatility': ['PEPE/USDT','SHIB/USDT']}

for tier, symbols in TIERS.items():
    fname = f'model_mean_reversion_v1_lstm_{tier.replace(" ","")}.pt'
    ckpt = torch.load(f'/app/models/{fname}', map_location='cpu', weights_only=False)
    cfg = ckpt.get('config', {})
    model = LSTMMeanReversion(3, cfg.get('hidden', 128), cfg.get('layers', 1))
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    
    for symbol in symbols:
        ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
        close = df['close'].values
        
        delta = np.diff(close, prepend=close[0])
        gain = np.maximum(delta, 0); loss = -np.minimum(delta, 0)
        avg_gain = pd.Series(gain).rolling(56).mean().values
        avg_loss = pd.Series(loss).rolling(56).mean().values
        rsi = 100 - 100/(1 + avg_gain/(avg_loss + 1e-10))
        rsi_s = pd.Series(rsi).ewm(span=2, adjust=False).mean().values
        rsi_4h = pd.Series(rsi).rolling(16).mean().values
        
        feats = np.column_stack([(rsi-50)/10, (rsi_s-50)/10, (rsi_4h-50)/10])
        feats = np.nan_to_num(feats[-144:])
        
        with torch.no_grad():
            score = model(torch.from_numpy(feats).unsqueeze(0).float()).item()
        rsi_now = rsi[-1]
        sinal = "SINAL" if rsi_now < 38 and score >= 0.65 else "------"
        print(f'{symbol:<12} {tier:<14} score={score:.4f} rsi={rsi_now:.1f} {sinal}')
