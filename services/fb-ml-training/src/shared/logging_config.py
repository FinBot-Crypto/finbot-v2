"""
Configuração de logging centralizada.
"""
import logging
import os

def setup_logging(level=logging.INFO):
    """
    Configura logging com formato padrão em todo o projeto.
    
    Args:
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_format = (
        '%(asctime)s - '
        '%(name)s - '
        '%(levelname)s - '
        '[%(filename)s:%(lineno)d] - '
        '%(message)s'
    )
    
    handlers = [
        logging.StreamHandler(),  # Console
    ]
    
    # Arquivo de log (opcional)
    log_dir = os.getenv('LOG_DIR', '/tmp/fb-ml-training')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'training.log')
    handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)
