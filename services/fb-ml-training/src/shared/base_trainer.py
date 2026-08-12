"""
Classe base abstrata para treinamento de todos os modelos.
"""
import logging
import os
import pickle
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from joblib import dump, load

logger = logging.getLogger(__name__)


class BaseTrainer(ABC):
    """
    Classe base abstrata para treinamento.
    Cada modelo concreto herda e configura seus parâmetros.
    """
    
    def __init__(self, model_name: str, version: str, tier: str, models_dir: str):
        """
        Inicializa o trainer.
        
        Args:
            model_name: Nome do modelo (ex: breakout, mean_reversion)
            version: Versão (v1, v2, v3)
            tier: Tier (Major, Strong Alt, High Volatility)
            models_dir: Diretório onde salvar modelos
        """
        self.model_name = model_name
        self.version = version
        self.tier = tier
        self.models_dir = models_dir
        self.model = None
        self.model_path = None
        
        logger.info(f"Trainer inicializado: {model_name}_{version} ({tier})")
    
    @abstractmethod
    def get_model_params(self) -> dict:
        """
        Deve ser implementado por cada modelo.
        Retorna parâmetros específicos do RandomForest para esta versão.
        
        Returns:
            Dict com parâmetros do RandomForestClassifier
        """
        pass
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> dict:
        """
        Treina o modelo RandomForest.
        
        Args:
            X_train: Features de treino
            y_train: Target de treino
        
        Returns:
            Dict com métricas de treinamento
        """
        logger.info(f"Iniciando treinamento de {self.model_name}_{self.version}...")
        logger.info(f"  X_train shape: {X_train.shape}")
        logger.info(f"  Classes: {y_train.value_counts().to_dict()}")
        
        # Criar modelo com parâmetros específicos
        params = self.get_model_params()
        self.model = RandomForestClassifier(
            **params,
            random_state=42,
            n_jobs=-1,
            verbose=1,
            class_weight='balanced_subsample'
        )
        
        # Guardar nomes das features
        self.feature_names_ = list(X_train.columns)
        
        # Treinar
        self.model.fit(X_train, y_train)
        
        # Métricas de treino
        y_pred_train = self.model.predict(X_train)
        y_proba_train = self.model.predict_proba(X_train)[:, 1]
        
        metrics = {
            'train_accuracy': accuracy_score(y_train, y_pred_train),
            'train_precision': precision_score(y_train, y_pred_train, zero_division=0),
            'train_recall': recall_score(y_train, y_pred_train, zero_division=0),
            'train_f1': f1_score(y_train, y_pred_train, zero_division=0),
            'train_auc': roc_auc_score(y_train, y_proba_train),
        }
        
        logger.info(f"✓ Treinamento concluído:")
        for k, v in metrics.items():
            logger.info(f"  {k}: {v:.4f}")
        
        return metrics
    
    def evaluate(self, X_val: pd.DataFrame, y_val: pd.Series) -> dict:
        """
        Avalia o modelo em dados de validação.
        
        Args:
            X_val: Features de validação
            y_val: Target de validação
        
        Returns:
            Dict com métricas de validação
        """
        if self.model is None:
            raise ValueError("Modelo não foi treinado")
        
        logger.info(f"Avaliando {self.model_name}_{self.version}...")
        
        y_pred_val = self.model.predict(X_val)
        y_proba_val = self.model.predict_proba(X_val)[:, 1]
        
        metrics = {
            'val_accuracy': accuracy_score(y_val, y_pred_val),
            'val_precision': precision_score(y_val, y_pred_val, zero_division=0),
            'val_recall': recall_score(y_val, y_pred_val, zero_division=0),
            'val_f1': f1_score(y_val, y_pred_val, zero_division=0),
            'val_auc': roc_auc_score(y_val, y_proba_val),
        }
        
        logger.info(f"✓ Avaliação concluída:")
        for k, v in metrics.items():
            logger.info(f"  {k}: {v:.4f}")
        
        return metrics
    
    def save_model(self, symbol: str) -> str:
        """
        Salva o modelo treinado em formato .joblib.
        
        Args:
            symbol: Par de trading (ex: BTC/USDT)
        
        Returns:
            Caminho do arquivo salvo
        """
        if self.model is None:
            raise ValueError("Modelo não foi treinado")
        
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Nome: model_{strategy}_{version}_{symbol}.joblib
        symbol_clean = symbol.replace('/', '_').replace('.', '_')
        filename = f"model_{self.model_name}_{self.version}_{symbol_clean}.joblib"
        self.model_path = os.path.join(self.models_dir, filename)
        
        dump(self.model, self.model_path)
        logger.info(f"✓ Modelo salvo em: {self.model_path}")
        
        return self.model_path
    
    def get_feature_importance(self, top_n: int = 10) -> pd.DataFrame:
        """
        Retorna as features mais importantes do modelo.
        
        Args:
            top_n: Número de top features
        
        Returns:
            DataFrame com feature names e importance
        """
        if self.model is None:
            raise ValueError("Modelo não foi treinado")
        
        importances = self.model.feature_importances_
        feature_names = getattr(self, 'feature_names_', None)
        
        if feature_names is None or len(feature_names) != len(importances):
            feature_names = [f'feature_{i}' for i in range(len(importances))]
        
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False).head(top_n)
        
        return importance_df
