"""
Trainer para modelo Breakout V1 (Major Tier - Donchian 15).
"""
import logging
from src.shared.base_trainer import BaseTrainer
from . import config

logger = logging.getLogger(__name__)


class BreakoutV1Trainer(BaseTrainer):
    """
    Trainer específico para Breakout V1.
    Herda de BaseTrainer e implementa parâmetros v1.
    """
    
    def __init__(self, models_dir: str):
        """Inicializa trainer para Breakout V1."""
        super().__init__(
            model_name="breakout",
            version="v1",
            tier=config.TIER,
            models_dir=models_dir
        )
    
    def get_model_params(self) -> dict:
        """
        Retorna parâmetros do RandomForest para Breakout V1.
        
        Returns:
            Dict com parâmetros
        """
        return {
            'n_estimators': config.N_ESTIMATORS,
            'max_depth': config.MAX_DEPTH,
            'min_samples_split': config.MIN_SAMPLES_SPLIT,
            'min_samples_leaf': config.MIN_SAMPLES_LEAF,
            'criterion': 'gini',
            'bootstrap': True,
            'max_features': 'sqrt',
        }
