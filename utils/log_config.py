import logging
import os
from datetime import datetime

import config

def setup_logging():
    """
    Setup logging
    """

    if logging.getLogger().hasHandlers():
        return
    
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d")

    log_directory = os.path.join(config.ABS_PATH, 'logs', year, month, day)

    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_filename = os.path.join(log_directory, "card.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_filename, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_format)
    logger.addHandler(stream_handler)

    logger.info("Configurado logging")