import logging
import os
from datetime import datetime

def setup_logging(log_name, logging_level):
    """Set up logging to console and file with a timestamped filename."""
    log_filename = f"logs/{log_name}_{datetime.now().strftime('%Y%m%d')}.log"
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)

    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger()
