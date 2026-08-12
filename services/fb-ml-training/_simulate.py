"""V3 detalhado: tabela completa + 5 dias aleatorios."""
import sys, asyncio, torch, numpy as np, pandas as pd
sys.path.insert(0, r'C:\Users\Renan\PythonProjects\financas_crypto_bot\services\fb-ml-training')
from src.shared.data_fetcher import DataFetcher
from src.shared.indicators import calculate_rsi
from src.shared.config import HIGH_VOL_SYMBOLS
from src.models.mean_reversion_v1.dataset import MeanReversionV1Dataset
from src.models.mean_reversion_v1.lstm_train import LSTMMeanReversion, make_sequences
from src.models.mean_reversion_v1 import config

device = 'cpu'
ckpt = torch.load(r'C:\Users\Renan\PythonProjects\financas_crypto_bot\services\fb-ml-training\models\model_mean_reversion_v1_lstm_HighVolatility.pt', map_location=device, weights_only=False)
cfg = ckpt.get('config', {})
feature_names = ckpt.get('feature_names', config.FEATURES)
model = LSTMMeanReversion(len(feature_names), 128, 1, 0).to(device)
model.load_state_dict(ckpt['model_state_dict']); model.eval()
seq = cfg.get('seq_len', 144)
TP, SL = 0.025, 0.02

async def main():
    f = DataFetcher(); all_data = []
    # Busca dados do BTC/USDT para usar como feature
    btc_df = await f.fetch_ohlcv("BTC/USDT", config.TIMEFRAME, config.CANDLES_TO_FETCH)
    for s in HIGH_VOL_SYMBOLS:
        df = await f.fetch_ohlcv(s, config.TIMEFRAME, config.CANDLES_TO_FETCH)
        if df is None: continue
        fr = await f.fetch_funding_rate_history(s, 1000)
        ds = MeanReversionV1Dataset(symbol=s).set_futures_data(funding_df=fr).set_btc_data(btc_df)
        X, y = ds.prepare(df)[1], ds.prepare(df)[3]
        X = X[feature_names]
        rsi_raw = calculate_rsi(df['close'], 56).tail(len(X)).values
        close_all = df['close'].values
        Xs, ys = make_sequences(X, y, seq)
        with torch.no_grad():
            p = model(torch.from_numpy(Xs).to(device)).numpy().flatten()
        for i in range(len(p)):
            idx = i+seq+seq; mx,mn=-np.inf,np.inf
            if idx>=len(close_all): continue
            entry=close_all[idx]
            for t in range(1,49):
                if idx+t<len(close_all): mx=max(mx,close_all[idx+t]); mn=min(mn,close_all[idx+t])
            rsi=rsi_raw[i+seq] if i+seq<len(rsi_raw) else 50
            close=close_all[idx] if idx<len(close_all) else 0
            all_data.append({'symbol':s,'score':p[i],'rsi':rsi,'max_ret':(mx/entry-1)*100,'min_ret':(mn/entry-1)*100,'dia':i//96,'close':close})

    df = pd.DataFrame(all_data)
    ndias = df['dia'].nunique()
    print(f"V3: {len(df)} candles, {df['symbol'].nunique()} ativos, {ndias} dias validacao")
    
    print(f"\nTabela completa (TP 2.5% / SL 2%):")
    print(f"{'RSI<':<5} {'Sc>=':<6} {'Trades':<8} {'Wins':<6} {'Loss':<6} {'Neutro':<7} {'WR':<7} {'/dia':<7} {'Lucro%':<10} {'$10k->R$'}")
    
    for rsi_t in [20, 25, 30, 35, 38, 40, 42, 45]:
        for sc_t in [0.90, 0.85, 0.80, 0.75, 0.70, 0.65]:
            sub = df[(df['rsi']<rsi_t)&(df['score']>=sc_t)]
            if len(sub)<5: continue
            w=(sub['max_ret']>=TP*100).sum(); l=(sub['min_ret']<=-SL*100).sum()
            n=len(sub)-w-l; wr=w/(w+l) if(w+l)>0 else 0
            lucro=w*TP-l*SL
            print(f"{rsi_t:<5} {sc_t:<6.2f} {len(sub):<8} {w:<6} {l:<6} {n:<7} {wr:<7.1%} {len(sub)/max(ndias,1):<7.1f} {lucro*100:<+10.1f} {10000*(1+lucro):<10.0f}")

    # 5 dias aleatorios com RSI<38 + score>=0.65
    rsi_t, sc_t = 38, 0.65
    print(f"\n5 dias aleatorios (RSI<{rsi_t} + score>={sc_t:.2f}):")
    np.random.seed(42)
    total_w, total_l, total_n, total_lucro = 0, 0, 0, 0
    for _ in range(5):
        d = np.random.choice(df['dia'].unique())
        day = df[(df['rsi']<rsi_t)&(df['score']>=sc_t)&(df['dia']==d)]
        if len(day)==0: continue
        w=(day['max_ret']>=TP*100).sum(); l=(day['min_ret']<=-SL*100).sum()
        n=len(day)-w-l; lucro=w*TP-l*SL
        total_w+=w; total_l+=l; total_n+=n; total_lucro+=lucro
        symbols = day['symbol'].nunique()
        print(f"  Dia {d+1:2d}: {len(day):3d} trades, {w}W/{l}L/{n}N, lucro={lucro*100:+.1f}% ({symbols} ativos)")
    
    print(f"\nTotal 5 dias: {total_w}W/{total_l}L/{total_n}N, WR={total_w/(total_w+total_l):.1%}, lucro={total_lucro*100:+.1f}%")

    # Por simbolo
    print(f"\nPor simbolo (RSI<{rsi_t} + score>={sc_t:.2f}):")
    for s in HIGH_VOL_SYMBOLS:
        sub = df[(df['symbol']==s)&(df['rsi']<rsi_t)&(df['score']>=sc_t)]
        w=(sub['max_ret']>=TP*100).sum(); l=(sub['min_ret']<=-SL*100).sum()
        n=len(sub)-w-l; wr=w/(w+l) if(w+l)>0 else 0
        print(f"  {s:<10} {len(sub):3d} trades, {w}W/{l}L/{n}N, WR={wr:.1%}")

asyncio.run(main())
