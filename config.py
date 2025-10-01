"""
Configuration for PDF Converter Service
"""
import os
from pathlib import Path

# Service Configuration
SERVICE_HOST = os.getenv('SERVICE_HOST', '0.0.0.0')
SERVICE_PORT = int(os.getenv('SERVICE_PORT', '8000'))

# Conversion Settings
CONVERSION_TIMEOUT = int(os.getenv('CONVERSION_TIMEOUT', '60'))  # seconds
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '52428800'))  # 50MB default

# Directory Settings
TEMP_DIR = os.getenv('TEMP_DIR', '/tmp')
LOG_DIR = os.getenv('LOG_DIR', 'logs')

# LibreOffice Settings
LIBREOFFICE_PATH = os.getenv('LIBREOFFICE_PATH', None)

# Cleanup Settings
CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', '600'))  # 10 minutes
MAX_FILE_AGE = int(os.getenv('MAX_FILE_AGE', '3600'))  # 1 hour

# Create directories if they don't exist
Path(LOG_DIR).mkdir(exist_ok=True)
Path(TEMP_DIR).mkdir(exist_ok=True)

# Logging Configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': os.path.join(LOG_DIR, 'pdf_converter.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': os.path.join(LOG_DIR, 'pdf_converter_errors.log'),
            'maxBytes': 5242880,  # 5MB
            'backupCount': 3,
        },
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'uvicorn': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'uvicorn.access': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
