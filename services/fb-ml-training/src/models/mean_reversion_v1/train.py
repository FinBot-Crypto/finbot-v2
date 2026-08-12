"""
Trainer para modelo Mean Reversion V1 (XGBoost Regressor).

Treina com eval_set para monitorar loss por iteração,
early stopping para evitar overfitting,
e retorna métricas de regressão (RMSE, MAE, R²).
"""
import logging
import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, roc_auc_score
from joblib import dump
from . import config

logger = logging.getLogger(__name__)


class MeanReversionV1Trainer:
    """
    Trainer XGBoost para Mean Reversion V1.
    Target: retorno contínuo. Score: sigmoid(prediction * 50).
    """

    def __init__(self, models_dir: str):
        self.model_name = "mean_reversion"
        self.version = "v1"
        self.tier = config.TIER
        self.models_dir = models_dir
        self.model = None
        self.model_path = None
        self.feature_names_ = None

        logger.info(f"Trainer XGBoost inicializado: {self.model_name}_{self.version} ({self.tier})")

    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
              X_val: pd.DataFrame, y_val: pd.Series) -> dict:
        """
        Treina XGBoost Regressor com eval_set e early stopping.
        Exibe RMSE a cada 50 iterações no log.
        """
        logger.info(f"Iniciando treinamento XGBoost {self.model_name}_{self.version}...")
        logger.info(f"  X_train: {X_train.shape} | X_val: {X_val.shape}")
        logger.info(f"  y_train: média={y_train.mean():.4%} std={y_train.std():.4%}")
        logger.info(f"  y_val:   média={y_val.mean():.4%} std={y_val.std():.4%}")

        self.feature_names_ = list(X_train.columns)

        self.model = xgb.XGBClassifier(
            n_estimators=config.N_ESTIMATORS,
            max_depth=config.MAX_DEPTH,
            learning_rate=config.LEARNING_RATE,
            objective='binary:logistic',
            eval_metric='logloss',
            subsample=config.SUBSAMPLE,
            colsample_bytree=config.COLSAMPLE_BYTREE,
            random_state=42,
        )

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_train, y_train), (X_val, y_val)],
            verbose=10,
        )

        train_proba = self.model.predict_proba(X_train)[:, 1]
        val_proba = self.model.predict_proba(X_val)[:, 1]
        train_pred = self.model.predict(X_train)
        val_pred = self.model.predict(X_val)

        metrics = {
            'train_logloss': float(-np.mean(y_train * np.log(train_proba + 1e-15) + (1 - y_train) * np.log(1 - train_proba + 1e-15))),
            'train_accuracy': float(accuracy_score(y_train, train_pred)),
            'train_auc': float(roc_auc_score(y_train, train_proba)),
            'val_logloss': float(-np.mean(y_val * np.log(val_proba + 1e-15) + (1 - y_val) * np.log(1 - val_proba + 1e-15))),
            'val_accuracy': float(accuracy_score(y_val, val_pred)),
            'val_auc': float(roc_auc_score(y_val, val_proba)),
        }

        logger.info(f"  Train LogLoss: {metrics['train_logloss']:.4f} | AUC: {metrics['train_auc']:.4f}")
        logger.info(f"  Val   LogLoss: {metrics['val_logloss']:.4f} | AUC: {metrics['val_auc']:.4f}")

        return metrics

    def evaluate(self, X_val: pd.DataFrame, y_val: pd.Series) -> dict:
        """Avalia o modelo e retorna métricas de classificação."""
        if self.model is None:
            raise ValueError("Modelo não foi treinado")

        proba = self.model.predict_proba(X_val)[:, 1]
        pred = self.model.predict(X_val)

        logloss = float(-np.mean(
            y_val * np.log(proba + 1e-15) + (1 - y_val) * np.log(1 - proba + 1e-15)
        ))

        metrics = {
            'val_logloss': logloss,
            'val_accuracy': float(accuracy_score(y_val, pred)),
            'val_auc': float(roc_auc_score(y_val, proba)),
        }

        logger.info(f"  Avaliação: LogLoss={logloss:.4f} AUC={metrics['val_auc']:.4f} Acc={metrics['val_accuracy']:.4f}")

        return metrics

    def save_model(self, symbol: str) -> str:
        """Salva modelo XGBoost como .joblib."""
        if self.model is None:
            raise ValueError("Modelo não foi treinado")

        os.makedirs(self.models_dir, exist_ok=True)

        symbol_clean = symbol.replace('/', '_').replace('.', '_')
        filename = f"model_{self.model_name}_{self.version}_{symbol_clean}.joblib"
        self.model_path = os.path.join(self.models_dir, filename)

        dump(self.model, self.model_path)
        logger.info(f"  Modelo salvo: {self.model_path}")

        return self.model_path

    def get_feature_importance(self, top_n: int = 10) -> pd.DataFrame:
        """Retorna feature importance do XGBoost."""
        if self.model is None:
            raise ValueError("Modelo não foi treinado")

        importance = self.model.feature_importances_
        names = self.feature_names_ or [f'f{i}' for i in range(len(importance))]

        return pd.DataFrame({
            'feature': names,
            'importance': importance
        }).sort_values('importance', ascending=False).head(top_n)
