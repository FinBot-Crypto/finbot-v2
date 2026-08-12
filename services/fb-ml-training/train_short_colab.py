"""
FinBot - Treinamento SHORT (Colab)
====================================
Treina 3 LSTMs (1 por tier) para prever QUEDA do RSI em 12h.
Target: RSI[t+12h] < RSI[t]  (invertido do LONG)
Uso no Colab (1 celula):
  !pip install -q ccxt pandas numpy torch scikit-learn
  %run train_short_colab.py
"""
import asyncio, logging, os, numpy as np, pandas as pd, torch, torch.nn as nn, ccxt
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import roc_auc_score, accuracy_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("train-short")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
EXCHANGE = ccxt.binance({"enableRateLimit": True})
os.makedirs("models", exist_ok=True)

TIERS = {
    "Major": {
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "seq": 144, "hidden": 128, "layers": 1, "dropout": 0.2,
        "epochs": 100, "lr": 0.0003, "batch": 32,
        "lookahead": 48, "tf": "15m", "candles": 6400,
    },
    "StrongAlt": {
        "symbols": ["SOL/USDT","MATIC/USDT","AVAX/USDT","LINK/USDT","DOGE/USDT","ADA/USDT","XRP/USDT"],
        "seq": 144, "hidden": 128, "layers": 1, "dropout": 0.3,
        "epochs": 100, "lr": 0.00015, "batch": 32,
        "lookahead": 48, "tf": "15m", "candles": 6400,
    },
    "HighVolatility": {
        "symbols": ["ARB/USDT","OP/USDT","LDO/USDT","ATOM/USDT","NEAR/USDT","INJ/USDT",
                     "PEPE/USDT","SHIB/USDT","MEME/USDT","GALA/USDT"],
        "seq": 144, "hidden": 128, "layers": 1, "dropout": 0.3,
        "epochs": 100, "lr": 0.00015, "batch": 32,
        "lookahead": 48, "tf": "15m", "candles": 6400,
    },
}


def rsi(closes, period=56):
    d = np.diff(closes)
    g = np.maximum(d, 0)
    l = -np.minimum(d, 0)
    ag, al = np.full(len(closes), np.nan), np.full(len(closes), np.nan)
    ag[period] = g[:period].mean()
    al[period] = l[:period].mean()
    for i in range(period + 1, len(closes)):
        ag[i] = (ag[i - 1] * (period - 1) + g[i - 1]) / period
        al[i] = (al[i - 1] * (period - 1) + l[i - 1]) / period
    rs = ag / np.where(al == 0, 1e-10, al)
    return pd.Series(np.where(al == 0, 100.0, 100 - 100 / (1 + rs)), index=closes.index)


def features(df):
    df = df.copy()
    df["rsi_14"] = rsi(df["close"])
    df["rsi_smooth"] = df["rsi_14"].ewm(span=2, adjust=False).mean()
    df["rsi_14_4h"] = df["rsi_14"].rolling(16).mean()
    return df.dropna()


def short_target(df, la):
    """Target SHORT: 1 se RSI vai CAIR (future < current)."""
    df = df.copy()
    f = df["rsi_smooth"].shift(-la)
    df["target"] = (f < df["rsi_smooth"]).astype(float)
    df.loc[df.index[-la:], "target"] = np.nan
    df = df.dropna(subset=["target"])
    log.info("  Target DOWN: %d/%d = %.1f%%", int(df["target"].sum()), len(df),
             int(df["target"].sum()) / max(len(df), 1) * 100)
    return df


def make_sequences(X, y, seq_len):
    vx = X.values.astype(np.float32)
    vy = y.values.astype(np.float32)
    xs, ys = [], []
    for i in range(seq_len, len(vx)):
        xs.append(vx[i - seq_len:i])
        ys.append(vy[i])
    return np.array(xs), np.array(ys)


class LSTMModel(nn.Module):
    def __init__(self, nf, hidden=128, layers=1, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(nf, hidden, layers, batch_first=True,
                            dropout=0 if layers == 1 else dropout)
        self.drop = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x):
        o, _ = self.lstm(x)
        return torch.sigmoid(self.fc(self.drop(o[:, -1, :])))


async def fetch(sym, tf, limit):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: EXCHANGE.fetch_ohlcv(sym, tf, limit=limit))


async def train_tier(cfg, name):
    log.info("\n%s", "=" * 60)
    log.info("TREINANDO SHORT: %s (%d symbols)", name, len(cfg["symbols"]))
    log.info("%s", "=" * 60)

    X_all, y_all = [], []
    for sym in cfg["symbols"]:
        raw = await fetch(sym, cfg["tf"], cfg["candles"])
        if not raw:
            log.warning("  Sem dados: %s", sym)
            continue
        df = pd.DataFrame(raw, columns=["ts","o","h","l","c","v"])
        df.index = pd.to_datetime(df["ts"], unit="ms")
        df = features(df)
        df = short_target(df, cfg["lookahead"])
        if len(df) < cfg["seq"] + 100:
            log.warning("  Dados insuficientes: %s (%d)", sym, len(df))
            continue
        split = int(len(df) * 0.7)
        X_all.append(df.iloc[split:][["rsi_14","rsi_smooth","rsi_14_4h"]])
        y_all.append(df.iloc[split:]["target"])
        log.info("  %s: %d val", sym, len(df) - split)

    if not X_all:
        log.error("  NENHUM dado valido")
        return None

    X = pd.concat(X_all).reset_index(drop=True)
    y = pd.concat(y_all).reset_index(drop=True)
    mu = X.mean()
    sg = X.std().replace(0, 1)
    X = (X - mu) / sg

    sp = int(len(X) * 0.7)
    Xs_tr, ys_tr = make_sequences(X.iloc[:sp], y.iloc[:sp], cfg["seq"])
    Xs_va, ys_va = make_sequences(X.iloc[sp:], y.iloc[sp:], cfg["seq"])
    log.info("  Sequencias: %d train, %d val", len(Xs_tr), len(Xs_va))

    bs = cfg["batch"]
    if len(Xs_tr) > 15000:
        bs = 24
    if len(Xs_tr) > 25000:
        bs = 16

    train_dl = DataLoader(TensorDataset(torch.from_numpy(Xs_tr), torch.from_numpy(ys_tr)), bs, True)
    val_dl = DataLoader(TensorDataset(torch.from_numpy(Xs_va), torch.from_numpy(ys_va)), bs, False)

    model = LSTMModel(3, cfg["hidden"], cfg["layers"], cfg["dropout"]).to(DEVICE)
    pw = (len(ys_tr) - ys_tr.sum()) / max(ys_tr.sum(), 1)
    crit = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pw]))
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="min", factor=0.5, patience=10)

    best_loss = float("inf")
    best_ep = 0
    wait = 0
    patience = 15

    for ep in range(cfg["epochs"]):
        model.train()
        tl = 0.0
        for Xb, yb in train_dl:
            Xb, yb = Xb.to(DEVICE), yb.to(DEVICE).unsqueeze(1)
            opt.zero_grad()
            loss = crit(model(Xb), yb)
            loss.backward()
            opt.step()
            tl += loss.item()

        model.eval()
        vl = 0.0
        with torch.no_grad():
            for Xb, yb in val_dl:
                vl += crit(model(Xb.to(DEVICE)), yb.to(DEVICE).unsqueeze(1)).item()

        tl /= len(train_dl)
        vl /= len(val_dl)
        sch.step(vl)

        if (ep + 1) % 20 == 0 or ep == 0:
            with torch.no_grad():
                p = np.concatenate([torch.sigmoid(model(Xb.to(DEVICE))).cpu().numpy().flatten()
                                    for Xb, _ in val_dl])
            log.info("  Ep%3d: tl=%.4f vl=%.4f auc=%.4f lr=%.6f",
                     ep + 1, tl, vl, roc_auc_score(ys_va, p),
                     opt.param_groups[0]["lr"])
        elif (ep + 1) % 5 == 0:
            log.info("  Ep%3d: tl=%.4f vl=%.4f", ep + 1, tl, vl)

        if vl < best_loss:
            best_loss = vl
            best_ep = ep
            wait = 0
            torch.save(model.state_dict(), f"models/best_{name}.pt")
        else:
            wait += 1
            if wait >= patience:
                model.load_state_dict(torch.load(f"models/best_{name}.pt"))
                log.info("  Early stop ep%d (best=%d)", ep + 1, best_ep + 1)
                break

    model.eval()
    with torch.no_grad():
        pva = np.concatenate([torch.sigmoid(model(Xb.to(DEVICE))).cpu().numpy().flatten()
                              for Xb, _ in val_dl])
    auc = roc_auc_score(ys_va, pva)
    acc = accuracy_score(ys_va, (pva >= 0.5).astype(int))
    log.info("  DONE: AUC=%.4f Acc=%.4f BestEp=%d", auc, acc, best_ep + 1)

    path = f"models/model_short_lstm_{name}.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "feature_names": ["rsi_14", "rsi_smooth", "rsi_14_4h"],
        "config": {"seq_len": cfg["seq"], "hidden": cfg["hidden"],
                   "layers": cfg["layers"], "dropout": cfg["dropout"], "n_features": 3},
    }, path)
    log.info("  Salvo: %s", path)
    return path


async def main():
    results = {}
    for name, cfg in TIERS.items():
        try:
            results[name] = await train_tier(cfg, name)
        except Exception as e:
            log.error("ERRO %s: %s", name, e, exc_info=True)

    print()
    print("=" * 60)
    print("TREINAMENTO CONCLUIDO")
    print("=" * 60)
    for name, r in results.items():
        if r:
            print(f"  {name}: {r}")
        else:
            print(f"  {name}: FALHOU")
    print()
    for f in sorted(os.listdir("models")):
        kb = os.path.getsize(f"models/{f}") / 1024
        print(f"  {f}  ({kb:.0f} KB)")
    print()
    print("Baixe os 3 model_short_lstm_*.pt")


if __name__ == "__main__":
    asyncio.run(main())
