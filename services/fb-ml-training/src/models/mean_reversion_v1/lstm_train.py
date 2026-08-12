"""
LSTM Trainer para Mean Reversion V1.
Classificacao binaria (direcao), BCE loss, sigmoid.
Score = 2 * predict_proba - 1.
"""
import logging, os, sys, numpy as np, pandas as pd, torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import accuracy_score, roc_auc_score
from joblib import dump
from . import config

logger = logging.getLogger(__name__)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def make_sequences(X, y, seq_len):
    X_vals = X.values if isinstance(X, pd.DataFrame) else X
    y_vals = y.values if isinstance(y, pd.Series) else y
    n = len(X_vals)
    X_seq, y_seq = [], []
    for i in range(seq_len, n):
        X_seq.append(X_vals[i - seq_len:i])
        y_seq.append(y_vals[i])
    return np.array(X_seq, dtype=np.float32), np.array(y_seq, dtype=np.float32)


class LSTMMeanReversion(nn.Module):
    def __init__(self, input_size, hidden_size=96, num_layers=1, dropout=0.4):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                            batch_first=True, dropout=0 if num_layers == 1 else dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last = lstm_out[:, -1, :]
        return torch.sigmoid(self.fc(self.dropout(last)))


class MeanReversionV1LSTMTrainer:
    def __init__(self, models_dir):
        self.model_name = "mean_reversion_v1_lstm"
        self.tier = config.TIER
        self.models_dir = models_dir
        self.model = None
        self.model_path = None
        self.feature_names_ = None
        logger.info(f"LSTM Trainer inicializado: {self.model_name} ({self.tier})")

    def train(self, X_train, y_train, X_val, y_val):
        seq_len = config.SEQ_LEN
        self.feature_names_ = list(X_train.columns)
        n_features = X_train.shape[1]

        Xs_tr, ys_tr = make_sequences(X_train, y_train, seq_len)
        Xs_va, ys_va = make_sequences(X_val, y_val, seq_len)

        logger.info(f"  Sequencias criadas: {len(Xs_tr)} train, {len(Xs_va)} val")
        logger.info(f"  Formato: (batch, {seq_len}, {n_features})")

        # Adaptive batch size: reduz quando tem muitos dados (evita OOM na T4)
        bs = config.BATCH_SIZE
        if len(Xs_tr) > 15000:
            bs = 24
        if len(Xs_tr) > 25000:
            bs = 16
        logger.info(f"  Batch size: {bs} (dataset: {len(Xs_tr)} train)")

        train_loader = DataLoader(
            TensorDataset(torch.from_numpy(Xs_tr), torch.from_numpy(ys_tr)),
            batch_size=bs, shuffle=True
        )
        val_loader = DataLoader(
            TensorDataset(torch.from_numpy(Xs_va), torch.from_numpy(ys_va)),
            batch_size=bs, shuffle=False
        )

        self.model = LSTMMeanReversion(
            input_size=n_features,
            hidden_size=config.LSTM_HIDDEN,
            num_layers=config.LSTM_LAYERS,
            dropout=config.DROPOUT,
        ).to(device)

        pos_weight = (len(ys_tr) - ys_tr.sum()) / max(ys_tr.sum(), 1)
        criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight]))
        # Wrap model with sigmoid for training compatibility
        # Actually BCEWithLogitsLoss takes raw logits, so remove sigmoid from forward
        # Let me use BCELoss instead with sigmoid already in forward
        criterion = nn.BCELoss()

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=config.LEARNING_RATE, weight_decay=config.WEIGHT_DECAY)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=10
        )

        best_val_auc = 0.0
        best_epoch = 0
        patience = 15
        wait = 0

        for epoch in range(config.EPOCHS):
            self.model.train()
            train_loss = 0
            for Xb, yb in train_loader:
                Xb, yb = Xb.to(device), yb.to(device).unsqueeze(1)
                optimizer.zero_grad()
                loss = criterion(self.model(Xb), yb)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for Xb, yb in val_loader:
                    Xb, yb = Xb.to(device), yb.to(device).unsqueeze(1)
                    loss = criterion(self.model(Xb), yb)
                    val_loss += loss.item()

            train_loss /= len(train_loader)
            val_loss /= len(val_loader)

            # Calcula AUC de validação a cada época
            self.model.eval()
            with torch.no_grad():
                p_va_batch = []
                for Xb, _ in val_loader:
                    p_va_batch.append(self.model(Xb.to(device)).cpu().numpy().flatten())
                p_va = np.concatenate(p_va_batch)
                val_auc = float(roc_auc_score(ys_va, p_va))

            scheduler.step(val_loss)

            logger.info(f"  Ep {epoch+1:3d}: loss_tr={train_loss:.4f} loss_val={val_loss:.4f} "
                        f"auc_val={val_auc:.4f} lr={optimizer.param_groups[0]['lr']:.6f}")
            sys.stdout.flush()

            if val_auc > best_val_auc:
                best_val_auc = val_auc
                best_epoch = epoch
                wait = 0
                torch.save(self.model.state_dict(), os.path.join(self.models_dir, f"{self.model_name}_best.pt"))
            else:
                wait += 1
                if wait >= patience:
                    logger.info(f"  Early stop ep {epoch+1} (best ep: {best_epoch+1}, best auc: {best_val_auc:.4f})")
                    self.model.load_state_dict(torch.load(os.path.join(self.models_dir, f"{self.model_name}_best.pt")))
                    break

        # Metrics (classificacao - batches NAO embaralhados)
        train_eval = DataLoader(TensorDataset(torch.from_numpy(Xs_tr), torch.from_numpy(ys_tr)), batch_size=config.BATCH_SIZE, shuffle=False)
        val_eval = DataLoader(TensorDataset(torch.from_numpy(Xs_va), torch.from_numpy(ys_va)), batch_size=config.BATCH_SIZE, shuffle=False)
        
        with torch.no_grad():
            tr_p, tr_y = [], []
            for Xb, yb in train_eval:
                tr_p.append(self.model(Xb.to(device)).cpu().numpy().flatten())
                tr_y.append(yb.numpy().flatten())
            train_proba, train_true = np.concatenate(tr_p), np.concatenate(tr_y)
            
            va_p, va_y = [], []
            for Xb, yb in val_eval:
                va_p.append(self.model(Xb.to(device)).cpu().numpy().flatten())
                va_y.append(yb.numpy().flatten())
            val_proba, val_true = np.concatenate(va_p), np.concatenate(va_y)

        train_pred = (train_proba >= 0.5).astype(int)
        val_pred = (val_proba >= 0.5).astype(int)

        metrics = {
            'train_loss': float(criterion(torch.from_numpy(train_proba), torch.from_numpy(train_true)).item()),
            'train_acc': float(accuracy_score(train_true, train_pred)),
            'train_auc': float(roc_auc_score(train_true, train_proba)),
            'val_loss': float(criterion(torch.from_numpy(val_proba), torch.from_numpy(val_true)).item()),
            'val_acc': float(accuracy_score(val_true, val_pred)),
            'val_auc': float(roc_auc_score(val_true, val_proba)),
            'best_epoch': best_epoch + 1,
        }

        logger.info(f"  Train Acc: {metrics['train_acc']:.4f} | AUC: {metrics['train_auc']:.4f}")
        logger.info(f"  Val   Acc: {metrics['val_acc']:.4f} | AUC: {metrics['val_auc']:.4f}")
        logger.info(f"  Pred stats: media={val_proba.mean():.4f} std={val_proba.std():.4f} "
                    f"min={val_proba.min():.4f} max={val_proba.max():.4f}")

        return metrics

    def evaluate(self, X_val, y_val):
        if self.model is None:
            raise ValueError("Modelo nao foi treinado")
        seq_len = config.SEQ_LEN
        Xs_va, ys_va = make_sequences(X_val, y_val, seq_len)
        with torch.no_grad():
            proba = self.model(torch.from_numpy(Xs_va).to(device)).cpu().numpy().flatten()
        pred = (proba >= 0.5).astype(int)
        metrics = {
            'val_loss': float(nn.BCELoss()(torch.from_numpy(proba), torch.from_numpy(ys_va)).item()),
            'val_acc': float(accuracy_score(ys_va, pred)),
            'val_auc': float(roc_auc_score(ys_va, proba)),
        }
        logger.info(f"  Val: Loss={metrics['val_loss']:.4f} Acc={metrics['val_acc']:.4f} AUC={metrics['val_auc']:.4f}")
        return metrics

    def _fast_predict(self, X):
        with torch.no_grad():
            return self.model(torch.from_numpy(X).to(device)).cpu().numpy().flatten()

    def predict_score(self, X):
        """Score [-1, +1]: 2 * proba - 1."""
        seq_len = config.SEQ_LEN
        if len(X) < seq_len:
            return np.zeros(len(X))
        Xs, _ = make_sequences(X, np.zeros(len(X)), seq_len)
        with torch.no_grad():
            proba = self.model(torch.from_numpy(Xs).to(device)).cpu().numpy().flatten()
        score = 2 * proba - 1
        full = np.zeros(len(X))
        full[seq_len:] = score
        return full

    def predict_proba(self, X):
        """Probabilidade [0, 1] para compatibilidade."""
        seq_len = config.SEQ_LEN
        if len(X) < seq_len:
            return np.column_stack([np.ones(len(X)) * 0.5, np.ones(len(X)) * 0.5])
        Xs, _ = make_sequences(X, np.zeros(len(X)), seq_len)
        with torch.no_grad():
            proba = self.model(torch.from_numpy(Xs).to(device)).cpu().numpy().flatten()
        full = np.full(len(X), 0.5)
        full[seq_len:] = proba
        return np.column_stack([1 - full, full])

    def save_model(self, tier_name):
        os.makedirs(self.models_dir, exist_ok=True)
        self.model_path = os.path.join(self.models_dir, f"model_{self.model_name}_{tier_name}.pt")
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'feature_names': self.feature_names_,
            'config': {
                'seq_len': config.SEQ_LEN,
                'hidden': config.LSTM_HIDDEN,
                'layers': config.LSTM_LAYERS,
                'dropout': config.DROPOUT,
                'n_features': len(self.feature_names_),
            }
        }, self.model_path)
        logger.info(f"  Modelo salvo: {self.model_path}")
        return self.model_path

    def predict_score(self, X):
        """Retorna score [-1, +1] para cada candle."""
        seq_len = config.SEQ_LEN
        if len(X) < seq_len:
            return np.zeros(len(X))
        Xs, _ = make_sequences(X, np.zeros(len(X)), seq_len)
        with torch.no_grad():
            score = self.model(torch.from_numpy(Xs).to(device)).cpu().numpy().flatten()
        full = np.zeros(len(X))
        full[seq_len:] = score
        return full
