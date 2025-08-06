import pandas as pd
import logging
import os
from datetime import datetime, timedelta

# Configuração do fuso horário de Brasília (UTC-3)
class BrasiliaTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created) - timedelta(hours=3)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()

def setup_logger():
    # Cria a pasta de logs se não existir
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Obtém a data/hora atual no fuso de Brasília
    now_brasilia = datetime.utcnow() - timedelta(hours=3)
    log_filename = now_brasilia.strftime("cardapio_%Y-%m-%d_%H-%M-%S.log")
    log_path = os.path.join(log_dir, log_filename)
    
    # Configura o logger
    logger = logging.getLogger('cardapio_processor')
    logger.setLevel(logging.DEBUG)
    
    # Formatação com horário de Brasília
    formatter = BrasiliaTimeFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S (BRT)')
    
    # Handlers (arquivo e console)
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()
