import json
import os
import platform
from dotenv import load_dotenv
from error_handler import logger

load_dotenv()

config = os.getenv('WIN_CONFIG_PATH') if platform.system() == 'Windows' else os.getenv('UNIX_CONFIG_PATH')
try:
    with open(config) as f:
        config_data = json.load(f)
except FileNotFoundError:
    logger.error('Config file not found. Please check the path in the .env file.')
except Exception as e:
    logger.error(f'Error loading config file: {e}')
    raise e
