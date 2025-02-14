import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logger = logging.getLogger('task_bot')
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler(
    f'logs/task_bot_{datetime.now().strftime("%Y%m%d")}.log',
    encoding='utf-8'
)

# Create formatters and add it to handlers
log_format = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
console_handler.setFormatter(log_format)
file_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler) 