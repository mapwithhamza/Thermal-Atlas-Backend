import os
from pathlib import Path

class Config:
    """Base config."""
    # Base paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR.parent / 'data'
    
    # Data subdirectories
    RAW_DATA_DIR = DATA_DIR / 'raw'
    PROCESSED_DATA_DIR = DATA_DIR / 'processed'
    GEOJSON_DIR = DATA_DIR / 'geojson'
    RASTERS_DIR = DATA_DIR / 'rasters'
    EXPORTS_DIR = DATA_DIR / 'exports'
    
    # Security and API Keys
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-key-change-in-prod')
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    NASA_USERNAME = os.getenv('NASA_USERNAME')
    NASA_PASSWORD = os.getenv('NASA_PASSWORD')
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173').split(',')
    
    # Flask settings
    DEBUG = os.getenv('FLASK_DEBUG') == 'True'
    TESTING = False
    
    # File Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    
    @staticmethod
    def ensure_directories():
        """Ensure all data directories exist."""
        dirs = [
            Config.RAW_DATA_DIR, Config.PROCESSED_DATA_DIR, 
            Config.GEOJSON_DIR, Config.RASTERS_DIR, Config.EXPORTS_DIR
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            
# Ensure directories are created on import
Config.ensure_directories()
